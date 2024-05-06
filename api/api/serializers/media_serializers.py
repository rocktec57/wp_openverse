import logging
from collections import namedtuple
from typing import TypedDict

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import MaxValueValidator
from django.urls import reverse
from rest_framework import serializers
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.request import Request

from drf_spectacular.utils import extend_schema_serializer
from elasticsearch_dsl.response import Hit
from openverse_attribution.license import License

from api.constants import sensitivity
from api.constants.licenses import LICENSE_GROUPS
from api.constants.media_types import MediaType
from api.constants.parameters import COLLECTION, TAG
from api.constants.search import COLLECTIONS
from api.constants.sorting import DESCENDING, RELEVANCE, SORT_DIRECTIONS, SORT_FIELDS
from api.controllers import search_controller
from api.models.media import AbstractMedia
from api.serializers.base import BaseModelSerializer
from api.serializers.docs import (
    COLLECTION_HELP_TEXT,
    CREATOR_HELP_TEXT,
    EXCLUDED_SOURCE_HELP_TEXT,
    SOURCE_HELP_TEXT,
    TAG_HELP_TEXT,
    UNSTABLE_WARNING,
)
from api.serializers.fields import SchemableHyperlinkedIdentityField
from api.utils.help_text import make_comma_separated_help_text
from api.utils.url import add_protocol


logger = logging.getLogger(__name__)

#######################
# Request serializers #
#######################


class PaginatedRequestSerializer(serializers.Serializer):
    """This serializer passes pagination parameters from the query string."""

    field_names = [
        "page_size",
        "page",
    ]
    page_size = serializers.IntegerField(
        label="page_size",
        help_text=f"Number of results to return per page. "
        f"Maximum is {settings.MAX_AUTHED_PAGE_SIZE} for authenticated "
        f"requests, and {settings.MAX_ANONYMOUS_PAGE_SIZE} for "
        f"unauthenticated requests.",
        required=False,
        default=settings.MAX_ANONYMOUS_PAGE_SIZE,
        min_value=1,
    )
    page = serializers.IntegerField(
        label="page",
        help_text="The page of results to retrieve.",
        required=False,
        default=1,
        max_value=settings.MAX_PAGINATION_DEPTH,
        min_value=1,
    )

    def validate_page_size(self, value):
        request = self.context.get("request")
        is_anonymous = getattr(request, "auth", None) is None
        max_value = (
            settings.MAX_ANONYMOUS_PAGE_SIZE
            if is_anonymous
            else settings.MAX_AUTHED_PAGE_SIZE
        )

        validator = MaxValueValidator(
            max_value,
            message=serializers.IntegerField.default_error_messages["max_value"].format(
                max_value=max_value
            ),
        )

        if is_anonymous:
            try:
                validator(value)
            except (ValidationError, DjangoValidationError) as e:
                raise NotAuthenticated(
                    detail=e.message,
                    code=e.code,
                )
        else:
            validator(value)

        return value


@extend_schema_serializer(
    # Hide internal fields from documentation.
    # Also see `field_names` below.
    exclude_fields=[
        "internal__index",
    ],
)
class MediaSearchRequestSerializer(PaginatedRequestSerializer):
    """This serializer parses and validates search query string parameters."""

    DeprecatedParam = namedtuple("DeprecatedParam", ["original", "successor"])
    deprecated_params = [
        DeprecatedParam("li", "license"),
        DeprecatedParam("lt", "license_type"),
        DeprecatedParam("pagesize", "page_size"),
        DeprecatedParam("provider", "source"),
    ]
    field_names = [
        "q",
        "source",
        "excluded_source",
        "license",
        "license_type",
        "creator",
        "tags",
        COLLECTION,
        TAG,
        "title",
        "filter_dead",
        "extension",
        "mature",
        "unstable__sort_by",
        "unstable__sort_dir",
        "unstable__authority",
        "unstable__authority_boost",
        "unstable__include_sensitive_results",
    ]
    field_names.extend(PaginatedRequestSerializer.field_names)
    """
    Keep the fields names in sync with the actual fields below as this list is
    used to generate Swagger documentation.
    """

    q = serializers.CharField(
        label="query",
        help_text="A query string that should not exceed 200 characters in length",
        required=False,
    )
    source = serializers.CharField(
        label="provider",
        required=False,
    )
    excluded_source = serializers.CharField(
        label="excluded_provider",
        required=False,
    )
    tags = serializers.CharField(
        label="tags",
        help_text="Search by tag only. Cannot be used with `q`. The search "
        "is fuzzy, so `tags=cat` will match any value that includes the word "
        "`cat`. If the value contains space, items that contain any of the "
        "words in the value will match. To search for several values, join "
        "them with a comma.",
        required=False,
        max_length=200,
    )
    title = serializers.CharField(
        label="title",
        help_text="Search by title only. Cannot be used with `q`. The search is fuzzy,"
        " so `title=photo` will match any value that includes the word `photo`. "
        "If the value contains space, items that contain any of the words in the "
        "value will match. To search for several values, join them with a comma.",
        required=False,
        max_length=200,
    )
    creator = serializers.CharField(
        label="creator",
        help_text=CREATOR_HELP_TEXT,
        required=False,
        max_length=200,
    )
    unstable__collection = serializers.ChoiceField(
        source="collection",
        label="collection",
        choices=COLLECTIONS,
        help_text=COLLECTION_HELP_TEXT,
        required=False,
    )
    unstable__tag = serializers.CharField(
        label="tag",
        source="tag",
        help_text=TAG_HELP_TEXT,
        required=False,
        max_length=200,
    )
    license = serializers.CharField(
        label="licenses",
        help_text=make_comma_separated_help_text(LICENSE_GROUPS["all"], "licenses"),
        required=False,
    )
    license_type = serializers.CharField(
        label="license type",
        help_text=make_comma_separated_help_text(
            LICENSE_GROUPS.keys(), "license types"
        ),
        required=False,
    )
    filter_dead = serializers.BooleanField(
        label="filter_dead",
        help_text="Control whether 404 links are filtered out.",
        required=False,
        default=settings.FILTER_DEAD_LINKS_BY_DEFAULT,
    )
    extension = serializers.CharField(
        label="extension",
        help_text="A comma separated list of desired file extensions.",
        required=False,
    )
    mature = serializers.BooleanField(
        label="mature",
        default=False,
        required=False,
        help_text="Whether to include sensitive content.",
    )

    # The ``unstable__`` prefix is used in the query params.
    # The validated data does not contain the ``unstable__`` prefix.
    # If you rename these fields, update the following references:
    #   - ``field_names`` in ``MediaSearchRequestSerializer``
    #   - validators for these fields in ``MediaSearchRequestSerializer``
    unstable__sort_by = serializers.ChoiceField(
        source="sort_by",
        help_text=f"{UNSTABLE_WARNING}The field which should be the basis for sorting results.",
        choices=SORT_FIELDS,
        required=False,
        default=RELEVANCE,
    )
    unstable__sort_dir = serializers.ChoiceField(
        source="sort_dir",
        help_text=f"{UNSTABLE_WARNING}The direction of sorting. Cannot be applied when sorting by "
        "`relevance`.",
        choices=SORT_DIRECTIONS,
        required=False,
        default=DESCENDING,
    )
    unstable__authority = serializers.BooleanField(
        label="authority",
        help_text=f"{UNSTABLE_WARNING}If enabled, the search will add a boost to results that are "
        "from authoritative sources.",
        required=False,
        default=False,
    )
    unstable__authority_boost = serializers.FloatField(
        label="authority_boost",
        help_text=f"{UNSTABLE_WARNING}The boost coefficient to apply to authoritative sources, "
        "multiplied with the popularity boost.",
        required=False,
        default=1.0,
        min_value=0.0,
        max_value=10.0,
    )
    unstable__include_sensitive_results = serializers.BooleanField(
        source="include_sensitive_results",
        label="include_sensitive_results",
        help_text=f"{UNSTABLE_WARNING}Whether to include results considered sensitive.",
        required=False,
        default=False,
    )

    # The ``internal__`` prefix is used in the query params.
    # If you rename these fields, update the following references:
    #   - ``field_names`` in ``MediaSearchRequestSerializer``
    #   - validators for these fields in ``MediaSearchRequestSerializer``
    internal__index = serializers.CharField(
        source="index",
        help_text="The index against which to perform the search.",
        required=False,
    )

    class Context(TypedDict, total=True):
        warnings: list[dict]
        media_type: MediaType
        request: Request

    context: Context

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context["warnings"] = []
        self.media_type = self.context.get("media_type")
        if not self.media_type:
            raise ValueError(
                "The media request serializer's `media_type` context variable must be set."
            )
        media_path = {"image": "images", "audio": "audio"}[self.media_type]
        variables = {
            "origin": settings.CANONICAL_ORIGIN,
            "media_path": media_path,
            "collection_param": COLLECTION,
        }

        self.fields["source"].help_text = SOURCE_HELP_TEXT.format(**variables)
        self.fields["excluded_source"].help_text = EXCLUDED_SOURCE_HELP_TEXT.format(
            **variables
        )

    def is_request_anonymous(self):
        request = self.context.get("request")
        return getattr(request, "auth", None) is None

    @staticmethod
    def _truncate(value):
        max_length = 200
        return value if len(value) <= max_length else value[:max_length]

    def validate_q(self, value):
        return self._truncate(value)

    @staticmethod
    def validate_license(value):
        """Check whether license is a valid license code."""

        licenses = value.lower().split(",")
        for _license in licenses:
            if _license not in LICENSE_GROUPS["all"]:
                raise serializers.ValidationError(
                    f"License '{_license}' does not exist."
                )
        # lowers the case of the value before returning
        return value.lower()

    @staticmethod
    def validate_license_type(value):
        """Check whether license type is a known collection of licenses."""

        license_types = value.lower().split(",")
        license_groups = []
        for _type in license_types:
            if _type not in LICENSE_GROUPS:
                raise serializers.ValidationError(
                    f"License type '{_type}' does not exist."
                )
            license_groups.append(LICENSE_GROUPS[_type])
        intersected = set.intersection(*license_groups)
        return ",".join(intersected)

    def validate_unstable__collection(self, value):
        if self.initial_data.get("q", None) is not None:
            raise serializers.ValidationError(
                "The `collection` parameter cannot be used with the `q` parameter."
            )
        if value == "tag" and not self.initial_data.get(TAG):
            raise serializers.ValidationError(
                f"The `{TAG}` parameter is required when `{COLLECTION}` is set to `tag`."
            )
        if value == "source" and not self.initial_data.get("source"):
            raise serializers.ValidationError(
                f"The `source` parameter is required when `{COLLECTION}` is set to `source`."
            )
        if value == "creator" and not (
            self.initial_data.get("creator") and self.initial_data.get("source")
        ):
            raise serializers.ValidationError(
                f"The `creator` and `source` parameters are required when `{COLLECTION}` is set to `creator`."
            )
        return value

    def validate_source(self, value):
        """
        For the regular searches, split the value.lower() by comma and only return the
        source names that are in the search controller's sources list for the media type.
        For the collection=tag, return the value as is. It is ignored in the query builder.
        For source and creator collections, accept the value as is, without lower-casing
        or splitting, and check if it's in the valid source name list.
        This function validates the source and excluded_source fields, but `excluded_source`
        is ignored for collection requests.
        """
        allowed_sources = list(search_controller.get_sources(self.media_type).keys())
        sources_list = ", ".join([f"'{s}'" for s in allowed_sources])
        collection = self.initial_data.get(COLLECTION)

        # For collection=tag, return the value as is. It is ignored in the query builder.
        if collection == "tag":
            return value

        if collection:
            if value not in allowed_sources:
                raise serializers.ValidationError(
                    f"Invalid source parameter '{value}'. Use one of the valid sources: {sources_list}"
                )
            return value
        else:
            sources = set(value.lower().split(","))
            valid_sources = {source for source in sources if source in allowed_sources}
            if not valid_sources:
                # Raise only if there are _no_ valid sources selected
                # If the requester passed only `mispelled_museum_name1,mispelled_musesum_name2`
                # the request cannot move forward, as all the top responses will likely be from Flickr
                # which provides radically different responses than most other providers.
                # If even one source is valid, it won't be a problem, in which case we'll issue a warning
                raise serializers.ValidationError(
                    f"Invalid source parameter '{value}'. No valid sources selected. "
                    f"Refer to the source list for valid options: {sources_list}."
                )
            elif invalid_sources := (sources - valid_sources):
                available_sources_uri = self.context["request"].build_absolute_uri(
                    reverse(f"{self.media_type}-stats")
                )
                self.context["warnings"].append(
                    {
                        "code": "partially invalid source parameter",
                        "message": (
                            "The source parameter included non-existent sources. "
                            f"For a list of available sources, see {available_sources_uri}"
                        ),
                        "invalid_sources": invalid_sources,
                        "valid_sources": valid_sources,
                    }
                )

            return ",".join(valid_sources)

    def validate_excluded_source(self, input_sources):
        if "source" in self.initial_data:
            raise serializers.ValidationError(
                "Cannot set both 'source' and 'excluded_source'. "
                "Use exactly one of these."
            )
        return self.validate_source(input_sources)

    def validate_creator(self, value):
        return self._truncate(value)

    def validate_tags(self, value):
        return self._truncate(value)

    def validate_title(self, value):
        return self._truncate(value)

    def validate_unstable__sort_by(self, value):
        return RELEVANCE if self.is_request_anonymous() else value

    def validate_unstable__sort_dir(self, value):
        return DESCENDING if self.is_request_anonymous() else value

    def validate_unstable__authority(self, value):
        return False if self.is_request_anonymous() else value

    def validate_unstable__include_sensitive_results(
        self,
        value,
    ):
        exclusive_fields = ("mature", "unstable__include_sensitive_results")
        if all(f in self.initial_data for f in exclusive_fields):
            raise serializers.ValidationError(
                "`mature` and `unstable__include_sensitive_results` "
                "must not both be defined."
            )

        return self.initial_data.get("mature") or value

    def validate_internal__index(self, value):
        """
        Check whether the given index name is a valid index or alias. However,
        for unauthenticated requests, no check is performed and ``None`` is
        returned immediately.

        :param value: the provided index name to check
        :return: ``None`` if request is anonymous, the provided name if it is valid
        :raise: ``serializers.ValidationError`` if not anonymous and invalid index name
        """

        if self.is_request_anonymous():
            return None
        if not settings.ES.indices.exists(value):  # ``exists`` includes aliases.
            raise serializers.ValidationError(f"Invalid index name `{value}`.")

        if not value.startswith(self.media_type):
            raise serializers.ValidationError(f"Invalid index name `{value}`.")
        return value

    @staticmethod
    def validate_extension(value):
        return value.lower()

    def validate(self, data):
        data = super().validate(data)
        errors = {}
        for param, successor in self.deprecated_params:
            if param in self.initial_data:
                errors[param] = (
                    f"Parameter '{param}' is deprecated in this release of the API. "
                    f"Use '{successor}' instead."
                )
        if errors:
            raise serializers.ValidationError(errors)

        return data


class MediaThumbnailRequestSerializer(serializers.Serializer):
    """This serializer parses and validates thumbnail query string parameters."""

    full_size = serializers.BooleanField(
        source="is_full_size",
        allow_null=True,
        required=False,
        default=False,
        help_text="whether to render the actual image and not a thumbnail version",
    )
    compressed = serializers.BooleanField(
        source="is_compressed",
        allow_null=True,
        default=None,
        required=False,
        help_text="whether to compress the output image to reduce file size,"
        "defaults to opposite of `full_size`",
    )

    def validate(self, data):
        if data.get("is_compressed") is None:
            data["is_compressed"] = not data["is_full_size"]
        return data


class MediaReportRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = None
        fields = ["identifier", "reason", "description"]
        read_only_fields = ["identifier"]

    def to_internal_value(self, data):
        """
        Map data before validation.

        See ``MediaReportRequestSerializer::_map_reason`` docstring for
        further explanation.
        """

        data["reason"] = self._map_reason(data.get("reason"))
        return super().to_internal_value(data)

    def validate(self, attrs):
        if (
            attrs["reason"] == "other"
            and ("description" not in attrs or len(attrs["description"])) < 20
        ):
            raise serializers.ValidationError(
                "Description must be at least be 20 characters long"
            )

        return attrs

    def _map_reason(self, value):
        """
        Map `sensitive` to `mature` for forwards compatibility.

        This is an interim implementation until the API is updated
        to use the new "sensitive" terminology.

        Once the API is updated to use "sensitive" as the designator
        rather than the current "mature" term, this function should
        be updated to reverse the mapping, that is, map `mature` to
        `sensitive`, for backwards compatibility.

        Note: This cannot be implemented as a simpler `validate_reason` method
        on the serializer because field validation runs _before_ validators
        declared on the serializer. This means the choice field's validation
        will complain about `reason` set to the incorrect value before we have
        a chance to map it to the correct value.

        This could be mitigated by adding all values, current, future, and
        deprecated, to the model field. However, that requires a migration
        each time we make that change, and would send an incorrect message
        about our data expectations. It's cleaner and more consistent to map
        the data up-front, at serialization time, to prevent any confusion at
        the data model level.
        """

        return "mature" if value == "sensitive" else value


########################
# Response serializers #
########################


class TagSerializer(serializers.Serializer):
    """This output serializer serializes a singular tag."""

    name = serializers.CharField(
        help_text="The name of a detailed tag.",
    )
    accuracy = serializers.FloatField(
        default=None,
        allow_null=True,
        help_text="The accuracy of a machine-generated tag. Human-generated "
        "tags have a null accuracy field.",
    )


@extend_schema_serializer(
    exclude_fields=[
        "unstable__sensitivity",
    ],
)
class MediaSerializer(BaseModelSerializer):
    """
    This serializer serializes a single media file.

    The class should be inherited by all individual media serializers.
    """

    class Meta:
        model = AbstractMedia
        fields = [
            "id",
            "indexed_on",
            "title",
            "foreign_landing_url",
            "url",
            "creator",
            "creator_url",
            "license",
            "license_version",
            "license_url",  # property
            "provider",
            "source",
            "category",
            "filesize",
            "filetype",
            "tags",
            "attribution",  # property
            "fields_matched",
            "mature",
            "unstable__sensitivity",
        ]
        """
        Keep the fields names in sync with the actual fields below as this list is
        used to generate Swagger documentation.
        """

    id = serializers.CharField(
        help_text="Our unique identifier for an open-licensed work.",
        source="identifier",
    )

    indexed_on = serializers.DateTimeField(
        source="created_on",
        help_text="The timestamp of when the media was indexed by Openverse.",
    )

    tags = TagSerializer(
        allow_null=True,  # replaced with ``[]`` in ``to_representation`` below
        many=True,
        help_text="Tags with detailed metadata, such as accuracy.",
    )

    fields_matched = serializers.ListField(
        allow_null=True,  # replaced with ``[]`` in ``to_representation`` below
        help_text="List the fields that matched the query for this result.",
    )

    mature = serializers.BooleanField(
        help_text="Whether the media item is marked as mature",
        source="sensitive",
    )

    # This should be promoted to a stable field alongside
    # `include_sensitive_results`
    unstable__sensitivity = serializers.SerializerMethodField(
        help_text=(
            "An array of sensitivity annotations. "
            "May contain the following values: 'sensitive_text', "
            "'user_reported_sensitive', or 'provider_supplied_sensitive'"
        )
    )

    def get_unstable__sensitivity(self, obj: Hit | AbstractMedia) -> list[str]:
        result = []

        # obj.identifier needs to be cast to a string because
        # Django UUID fields return UUID objects by default
        # and UUID comparison fails against _any_ string object,
        # even if the string matches the UUID.
        if str(obj.identifier) in self.context.get(
            "sensitive_text_result_identifiers", set()
        ):
            result.append(sensitivity.TEXT)

        # ``obj.sensitive`` will either be `mature` from the ES document (see below)
        # or the ``sensitive`` property on the Image or Audio model.
        if obj.sensitive:
            # We do not currently have any documents marked `mature=true`
            # that were not marked so as a result of a confirmed user report.
            # This is despite the fact that the ingestion server _does_ copy
            # the mature field from record `meta_data`. If you query for
            # documents in the production image and audio indexes that have
            # `mature=true` but do not have confirmed reports, you will get
            # 0 results. Whether this is because we truly do not have results
            # that providers have themselves marked as mature, unsafe, etc,
            # it isn't clear (aside from Flickr, where we use "safe search").
            # What is clear is that we do not need to handle provider reported
            # sensitivity here because it simply does not occur in our database.
            # That is _very_ convenient because provider supplied maturity is
            # much more complex to derive. Its condition is that the result
            # has no report _and_ has `mature=true` on the document in ES.
            # The only way to derive that is to query both the database and
            # Elasticsearch (or have access to both of those individually).
            # Due to the flexibility of this serializer in being able to
            # handle both Elasticsearch ``Hit``s _and_ media model instances,
            # trying to handle provider supplied maturity significantly
            # increases complexity here and, in order to prevent redundant
            # queries to either Postgres or ES, in other parts of the codebase.
            result.append(sensitivity.USER_REPORTED)

        return result

    def to_representation(self, *args, **kwargs):
        # This serializer adapts both ES Hits *and* Media instances. Currently,
        # ES has a `mature` field on it which represents if maturity was present on
        # the record in the database. The attributes in the code have been renamed
        # to `sensitive`, but for the time being this flag still exists on the ES index.
        # In order to prevent failures in serialization (since the serializer is looking
        # for the `sensitive` attribute), we rename it here.
        obj = args[0]
        if isinstance(obj, Hit):
            obj.sensitive = obj.mature

        output = super().to_representation(*args, **kwargs)

        # Ensure lists are ``[]`` instead of ``None``
        # TODO: These fields are still marked 'Nullable' in the API docs
        list_fields = ["tags", "fields_matched"]
        for list_field in list_fields:
            if output[list_field] is None:
                output[list_field] = []

        # Ensure license is lowercase
        output["license"] = output["license"].lower()

        if output.get("license_url") is None:
            try:
                lic = License(output["license"], output["license_version"])
                output["license_url"] = lic.url
            except ValueError:
                pass

        # Ensure URLs have scheme
        url_fields = ["url", "creator_url", "foreign_landing_url"]
        for url_field in url_fields:
            output[url_field] = add_protocol(output[url_field])

        return output


#######################
# Dynamic serializers #
#######################


def get_hyperlinks_serializer(media_type):
    class MediaHyperlinksSerializer(serializers.Serializer):
        """
        This serializer creates URLs pointing to other endpoints for this media item.

        These URLs include the thumbnail, details page and list of related media.
        """

        field_names = [
            "thumbnail",  # Not suffixed with `_url` because it points to an image
            "detail_url",
            "related_url",
        ]
        """
        Keep the fields names in sync with the actual fields below as this list is
        used to generate Swagger documentation.
        """

        thumbnail = SchemableHyperlinkedIdentityField(
            read_only=True,
            view_name=f"{media_type}-thumb",
            lookup_field="identifier",
            help_text="A direct link to the miniature artwork.",
            # Some audio results do not have thumbnails
            allow_null=media_type == "audio",
        )
        detail_url = SchemableHyperlinkedIdentityField(
            read_only=True,
            view_name=f"{media_type}-detail",
            lookup_field="identifier",
            help_text="A direct link to the detail view of this audio file.",
        )
        related_url = SchemableHyperlinkedIdentityField(
            read_only=True,
            view_name=f"{media_type}-related",
            lookup_field="identifier",
            help_text="A link to an endpoint that provides similar audio files.",
        )

    return MediaHyperlinksSerializer
