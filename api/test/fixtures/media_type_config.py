from dataclasses import dataclass
from typing import Iterable

import pook
import pytest
from elasticsearch import Elasticsearch

from api.models import (
    Audio,
    DeletedAudio,
    DeletedImage,
    Image,
    SensitiveAudio,
    SensitiveImage,
)
from api.models.media import AbstractDeletedMedia, AbstractMedia, AbstractSensitiveMedia
from api.serializers.audio_serializers import (
    AudioReportRequestSerializer,
    AudioSearchRequestSerializer,
    AudioSerializer,
)
from api.serializers.image_serializers import (
    ImageReportRequestSerializer,
    ImageSearchRequestSerializer,
    ImageSerializer,
)
from api.serializers.media_serializers import (
    MediaReportRequestSerializer,
    MediaSearchRequestSerializer,
    MediaSerializer,
)
from test.factory import models as model_factories
from test.factory.models.media import (
    CREATED_BY_FIXTURE_MARKER,
    MediaFactory,
    MediaReportFactory,
)


@dataclass
class MediaTypeConfig:
    media_type: str
    url_prefix: str
    origin_index: str
    filtered_index: str
    model_factory: MediaFactory
    model_class: AbstractMedia
    sensitive_factory: MediaFactory
    sensitive_class: AbstractSensitiveMedia
    search_request_serializer: MediaSearchRequestSerializer
    model_serializer: MediaSerializer
    report_serializer: MediaReportRequestSerializer
    report_factory: MediaReportFactory
    deleted_class: AbstractDeletedMedia
    providers: Iterable[str]
    """providers for the media type from the sample data"""

    categories: Iterable[str]
    """categories for the media type from the sample data"""

    tags: Iterable[str]
    """tags for the media type from the sample data"""

    q: str
    """a search query for this media type that yields some results"""

    @property
    def indexes(self):
        return (self.origin_index, self.filtered_index)


MEDIA_TYPE_CONFIGS = {
    "image": MediaTypeConfig(
        media_type="image",
        url_prefix="images",
        origin_index="image",
        filtered_index="image-filtered",
        model_factory=model_factories.ImageFactory,
        model_class=Image,
        sensitive_factory=model_factories.SensitiveImageFactory,
        search_request_serializer=ImageSearchRequestSerializer,
        model_serializer=ImageSerializer,
        report_serializer=ImageReportRequestSerializer,
        report_factory=model_factories.ImageReportFactory,
        sensitive_class=SensitiveImage,
        deleted_class=DeletedImage,
        providers=("flickr", "stocksnap"),
        categories=("photograph",),
        tags=("cat", "Cat"),
        q="dog",
    ),
    "audio": MediaTypeConfig(
        media_type="audio",
        url_prefix="audio",
        origin_index="audio",
        filtered_index="audio-filtered",
        model_factory=model_factories.AudioFactory,
        model_class=Audio,
        sensitive_factory=model_factories.SensitiveAudioFactory,
        search_request_serializer=AudioSearchRequestSerializer,
        model_serializer=AudioSerializer,
        report_serializer=AudioReportRequestSerializer,
        report_factory=model_factories.AudioReportFactory,
        sensitive_class=SensitiveAudio,
        deleted_class=DeletedAudio,
        providers=("freesound", "jamendo", "wikimedia_audio", "ccmixter"),
        categories=("music", "pronunciation"),
        tags=("cat",),
        q="love",
    ),
}


@pytest.fixture
def image_media_type_config():
    return MEDIA_TYPE_CONFIGS["image"]


@pytest.fixture
def audio_media_type_config():
    return MEDIA_TYPE_CONFIGS["audio"]


@pytest.fixture(
    params=MEDIA_TYPE_CONFIGS.values(),
    ids=lambda x: f"{x.media_type}_media_type_config",
)
def media_type_config(request: pytest.FixtureRequest) -> MediaTypeConfig:
    assert request.param.providers in {
        MEDIA_TYPE_CONFIGS["image"].providers,
        MEDIA_TYPE_CONFIGS["audio"].providers,
    }
    return request.param


@pytest.fixture(autouse=True)
def cleanup_elasticsearch_test_documents(request, settings):
    yield None
    # This fixture only matters after tests are finished

    if not request.node.get_closest_marker("django_db"):
        # If the test isn't configured to access the database
        # then it couldn't have created any new documents,
        # so we can skip cleanup
        return

    es: Elasticsearch = settings.ES

    # If pook was activated by a test and not deactivated
    # (usually because the test failed and something prevent
    # pook from cleaning up after itself), disable here so that
    # the ES request on the next line doesn't get intercepted,
    # causing pook to raise an exception about the request not
    # matching and the fixture documents not getting cleaned.
    pook.disable()

    es.delete_by_query(
        index="*",
        query={"match": {"tags.name": CREATED_BY_FIXTURE_MARKER}},
        refresh=True,
    )
