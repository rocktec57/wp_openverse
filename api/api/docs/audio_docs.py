from drf_spectacular.utils import OpenApiResponse, extend_schema

from api.docs.base_docs import collection_schema, custom_extend_schema, fields_to_md
from api.examples import (
    audio_complain_201_example,
    audio_complain_curl,
    audio_detail_200_example,
    audio_detail_404_example,
    audio_detail_curl,
    audio_related_200_example,
    audio_related_404_example,
    audio_related_curl,
    audio_search_200_example,
    audio_search_400_example,
    audio_search_list_curl,
    audio_stats_200_example,
    audio_stats_curl,
    audio_waveform_200_example,
    audio_waveform_404_example,
    audio_waveform_curl,
)
from api.serializers.audio_serializers import (
    AudioReportRequestSerializer,
    AudioSearchRequestSerializer,
    AudioSerializer,
    AudioWaveformSerializer,
)
from api.serializers.error_serializers import (
    InputErrorSerializer,
    NotFoundErrorSerializer,
)
from api.serializers.media_serializers import MediaThumbnailRequestSerializer
from api.serializers.provider_serializers import ProviderSerializer


search = custom_extend_schema(
    desc=f"""
        Search audio files using a query string.

        By using this endpoint, you can obtain search results based on specified
        query and optionally filter results by
        {fields_to_md(AudioSearchRequestSerializer.field_names)}.

        Results are ranked in order of relevance and paginated on the basis of the
        `page` param. The `page_size` param controls the total number of pages.

        Although there may be millions of relevant records, only the most relevant
        several thousand records can be viewed. This is by design: the search
        endpoint should be used to find the top 10,000 most relevant results, not
        for exhaustive search or bulk download of every barely relevant result. As
        such, the caller should not try to access pages beyond `page_count`, or else
        the server will reject the query.""",
    params=AudioSearchRequestSerializer,
    res={
        200: (AudioSerializer, audio_search_200_example),
        400: (InputErrorSerializer, audio_search_400_example),
    },
    eg=[audio_search_list_curl],
    external_docs={
        "description": "Openverse Syntax Guide",
        "url": "https://openverse.org/search-help",
    },
)

stats = custom_extend_schema(
    desc=f"""
        Get a list of all content providers and their respective number of
        audio files in the Openverse catalog.

        By using this endpoint, you can obtain info about content providers such
        as {fields_to_md(ProviderSerializer.Meta.fields)}.""",
    res={200: (ProviderSerializer, audio_stats_200_example)},
    eg=[audio_stats_curl],
)

detail = custom_extend_schema(
    desc=f"""
        Get the details of a specified audio track.

        By using this endpoint, you can obtain info about audio files such as
        {fields_to_md(AudioSerializer.Meta.fields)}""",
    res={
        200: (AudioSerializer, audio_detail_200_example),
        404: (NotFoundErrorSerializer, audio_detail_404_example),
    },
    eg=[audio_detail_curl],
)

related = custom_extend_schema(
    desc=f"""
        Get related audio files for a specified audio track.

        By using this endpoint, you can get the details of related audio such as
        {fields_to_md(AudioSerializer.Meta.fields)}.""",
    res={
        200: (AudioSerializer(many=True), audio_related_200_example),
        404: (NotFoundErrorSerializer, audio_related_404_example),
    },
    eg=[audio_related_curl],
)

report = custom_extend_schema(
    res={201: (AudioReportRequestSerializer, audio_complain_201_example)},
    eg=[audio_complain_curl],
)

thumbnail = extend_schema(
    parameters=[MediaThumbnailRequestSerializer],
    responses={200: OpenApiResponse(description="Thumbnail image")},
)

waveform = custom_extend_schema(
    res={
        200: (AudioWaveformSerializer, audio_waveform_200_example),
        404: (NotFoundErrorSerializer, audio_waveform_404_example),
    },
    eg=[audio_waveform_curl],
)

source_collection = collection_schema(
    media_type="audio",
    collection="source",
)
creator_collection = collection_schema(
    media_type="audio",
    collection="creator",
)
tag_collection = collection_schema(
    media_type="audio",
    collection="tag",
)
