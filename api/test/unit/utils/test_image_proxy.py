import asyncio
from dataclasses import replace
from test.factory.models.image import ImageFactory
from urllib.parse import urlencode

from django.conf import settings
from rest_framework.exceptions import UnsupportedMediaType

import aiohttp
import pook
import pytest
from aiohttp import client_exceptions
from aiohttp.client_reqrep import ConnectionKey

from api.utils.image_proxy import (
    HEADERS,
    MediaInfo,
    RequestConfig,
    UpstreamThumbnailException,
    extension,
)
from api.utils.image_proxy import get as _photon_get
from api.utils.tallies import get_monthly_timestamp


TEST_IMAGE_DOMAIN = "subdomain.example.com"
PHOTON_URL_FOR_TEST_IMAGE = (
    f"{settings.PHOTON_ENDPOINT}{TEST_IMAGE_DOMAIN}/path_part1/part2/image_dot_jpg.jpg"
)
TEST_IMAGE_URL = PHOTON_URL_FOR_TEST_IMAGE.replace(settings.PHOTON_ENDPOINT, "http://")
TEST_MEDIA_IDENTIFIER = "123"
TEST_MEDIA_PROVIDER = "foo"

TEST_MEDIA_INFO = MediaInfo(
    media_identifier=TEST_MEDIA_IDENTIFIER,
    media_provider=TEST_MEDIA_PROVIDER,
    image_url=TEST_IMAGE_URL,
)

UA_HEADER = HEADERS["User-Agent"]

MOCK_BODY = "mock response body"

SVG_BODY = """<?xml version="1.0" encoding="UTF-8"?>
<svg version="1.1" xmlns="http://www.w3.org/2000/svg">
<text x="10" y="10" fill="white">SVG</text>
</svg>"""


@pytest.fixture
def auth_key():
    test_key = "this is a test Photon Key boop boop, let me in"
    settings.PHOTON_AUTH_KEY = test_key

    yield test_key

    settings.PHOTON_AUTH_KEY = None


@pytest.fixture
def photon_get(session_loop):
    """
    Run ``image_proxy.get`` and wait for all tasks to finish.
    """

    def do(*args, **kwargs):
        try:
            res = session_loop.run_until_complete(_photon_get(*args, **kwargs))
            return res
        finally:
            tasks = asyncio.all_tasks(session_loop)
            for task in tasks:
                session_loop.run_until_complete(task)

    yield do


@pook.on
def test_get_successful_no_auth_key_default_args(photon_get, mock_image_data):
    mock_get: pook.Mock = (
        pook.get(PHOTON_URL_FOR_TEST_IMAGE)
        .params(
            {
                "w": settings.THUMBNAIL_WIDTH_PX,
                "quality": settings.THUMBNAIL_QUALITY,
            }
        )
        .header("User-Agent", UA_HEADER)
        .header("Accept", "image/*")
        .reply(200)
        .body(MOCK_BODY)
        .mock
    )

    res = photon_get(TEST_MEDIA_INFO)

    assert res.content == MOCK_BODY.encode()
    assert res.status_code == 200
    assert mock_get.matched


@pook.on
def test_get_successful_original_svg_no_auth_key_default_args(
    photon_get, mock_image_data
):
    mock_get: pook.Mock = (
        pook.get(TEST_IMAGE_URL.replace(".jpg", ".svg"))
        .header("User-Agent", UA_HEADER)
        .header("Accept", "image/*")
        .reply(200)
        .body(SVG_BODY)
        .mock
    )

    media_info = replace(
        TEST_MEDIA_INFO, image_url=TEST_MEDIA_INFO.image_url.replace(".jpg", ".svg")
    )

    res = photon_get(media_info)

    assert res.content == SVG_BODY.encode()
    assert res.status_code == 200
    assert mock_get.matched


@pook.on
def test_get_successful_with_auth_key_default_args(
    photon_get, mock_image_data, auth_key
):
    mock_get: pook.Mock = (
        pook.get(PHOTON_URL_FOR_TEST_IMAGE)
        .params(
            {
                "w": settings.THUMBNAIL_WIDTH_PX,
                "quality": settings.THUMBNAIL_QUALITY,
            }
        )
        .header("User-Agent", UA_HEADER)
        .header("Accept", "image/*")
        .header("X-Photon-Authentication", auth_key)
        .reply(200)
        .body(MOCK_BODY)
        .mock
    )

    res = photon_get(TEST_MEDIA_INFO)

    assert res.content == MOCK_BODY.encode()
    assert res.status_code == 200
    assert mock_get.matched


@pook.on
def test_get_successful_no_auth_key_not_compressed(photon_get, mock_image_data):
    mock_get: pook.Mock = (
        pook.get(PHOTON_URL_FOR_TEST_IMAGE)
        .params(
            {
                "w": settings.THUMBNAIL_WIDTH_PX,
            }
        )
        .header("User-Agent", UA_HEADER)
        .header("Accept", "image/*")
        .reply(200)
        .body(MOCK_BODY)
        .mock
    )

    res = photon_get(TEST_MEDIA_INFO, RequestConfig(is_compressed=False))

    assert res.content == MOCK_BODY.encode()
    assert res.status_code == 200
    assert mock_get.matched


@pook.on
def test_get_successful_no_auth_key_full_size(photon_get, mock_image_data):
    mock_get: pook.Mock = (
        pook.get(PHOTON_URL_FOR_TEST_IMAGE)
        .params(
            {
                "quality": settings.THUMBNAIL_QUALITY,
            }
        )
        .header("User-Agent", UA_HEADER)
        .header("Accept", "image/*")
        .reply(200)
        .body(MOCK_BODY)
        .mock
    )

    res = photon_get(TEST_MEDIA_INFO, RequestConfig(is_full_size=True))

    assert res.content == MOCK_BODY.encode()
    assert res.status_code == 200
    assert mock_get.matched


@pook.on
def test_get_successful_no_auth_key_full_size_not_compressed(
    photon_get, mock_image_data
):
    mock_get: pook.Mock = (
        pook.get(PHOTON_URL_FOR_TEST_IMAGE)
        .header("User-Agent", UA_HEADER)
        .header("Accept", "image/*")
        .reply(200)
        .body(MOCK_BODY)
        .mock
    )

    res = photon_get(
        TEST_MEDIA_INFO,
        RequestConfig(is_full_size=True, is_compressed=False),
    )

    assert res.content == MOCK_BODY.encode()
    assert res.status_code == 200
    assert mock_get.matched


@pook.on
def test_get_successful_no_auth_key_png_only(photon_get, mock_image_data):
    mock_get: pook.Mock = (
        pook.get(PHOTON_URL_FOR_TEST_IMAGE)
        .params(
            {
                "w": settings.THUMBNAIL_WIDTH_PX,
                "quality": settings.THUMBNAIL_QUALITY,
            }
        )
        .header("User-Agent", UA_HEADER)
        .header("Accept", "image/png")
        .reply(200)
        .body(MOCK_BODY)
        .mock
    )

    res = photon_get(TEST_MEDIA_INFO, RequestConfig(accept_header="image/png"))

    assert res.content == MOCK_BODY.encode()
    assert res.status_code == 200
    assert mock_get.matched


@pook.on
def test_get_successful_forward_query_params(photon_get, mock_image_data):
    params = urlencode({"hello": "world", 1: 2, "beep": "boop"})
    mock_get: pook.Mock = (
        pook.get(PHOTON_URL_FOR_TEST_IMAGE)
        .params(
            {
                "w": settings.THUMBNAIL_WIDTH_PX,
                "quality": settings.THUMBNAIL_QUALITY,
                "q": params,
            }
        )
        .header("User-Agent", UA_HEADER)
        .header("Accept", "image/*")
        .reply(200)
        .body(MOCK_BODY)
        .mock
    )

    media_info_with_url_params = replace(
        TEST_MEDIA_INFO, image_url=f"{TEST_IMAGE_URL}?{params}"
    )

    res = photon_get(media_info_with_url_params)

    assert res.content == MOCK_BODY.encode()
    assert res.status_code == 200
    assert mock_get.matched


@pytest.fixture
def setup_request_exception(monkeypatch):
    def do(exc):
        async def raise_exc(*args, **kwargs):
            raise exc

        monkeypatch.setattr(aiohttp.ClientSession, "get", raise_exc)

    yield do


@pook.on
def test_get_successful_records_response_code(photon_get, mock_image_data, redis):
    (
        pook.get(PHOTON_URL_FOR_TEST_IMAGE)
        .params(
            {
                "w": settings.THUMBNAIL_WIDTH_PX,
                "quality": settings.THUMBNAIL_QUALITY,
            }
        )
        .header("User-Agent", UA_HEADER)
        .header("Accept", "image/*")
        .reply(200)
        .body(MOCK_BODY)
        .mock
    )

    photon_get(TEST_MEDIA_INFO)
    month = get_monthly_timestamp()
    assert redis.get(f"thumbnail_response_code:{month}:200") == b"1"
    assert (
        redis.get(f"thumbnail_response_code_by_domain:{TEST_IMAGE_DOMAIN}:{month}:200")
        == b"1"
    )


alert_count_params = pytest.mark.parametrize(
    "count_start, should_alert",
    [
        (0, True),
        (1, True),
        (50, True),
        (99, True),
        (100, False),
        (999, True),
        (1000, False),
        (1500, False),
        (1999, True),
    ],
)

MOCK_CONNECTION_KEY = ConnectionKey(
    host="https://localhost",
    port=None,
    is_ssl=False,
    ssl=None,
    proxy=None,
    proxy_auth=None,
    proxy_headers_hash=None,
)


@pytest.mark.parametrize(
    "exc, exc_name",
    [
        (ValueError("whoops"), "builtins.ValueError"),
        (
            client_exceptions.ClientConnectionError("whoops"),
            "aiohttp.client_exceptions.ClientConnectionError",
        ),
        (
            client_exceptions.ServerTimeoutError("whoops"),
            "aiohttp.client_exceptions.ServerTimeoutError",
        ),
        (
            client_exceptions.ClientSSLError(MOCK_CONNECTION_KEY, OSError()),
            "aiohttp.client_exceptions.ClientSSLError",
        ),
        (
            client_exceptions.ClientOSError("whoops"),
            "aiohttp.client_exceptions.ClientOSError",
        ),
    ],
)
@alert_count_params
def test_get_exception_handles_error(
    photon_get,
    exc,
    exc_name,
    count_start,
    should_alert,
    sentry_capture_exception,
    setup_request_exception,
    redis,
):
    setup_request_exception(exc)
    month = get_monthly_timestamp()
    key = f"thumbnail_error:{exc_name}:{TEST_IMAGE_DOMAIN}:{month}"
    redis.set(key, count_start)

    with pytest.raises(UpstreamThumbnailException):
        photon_get(TEST_MEDIA_INFO)

    assert_func = (
        sentry_capture_exception.assert_called_once
        if should_alert
        else sentry_capture_exception.assert_not_called
    )
    assert_func()
    assert redis.get(key) == str(count_start + 1).encode()


@alert_count_params
@pytest.mark.parametrize(
    "status_code, text",
    [
        (400, "Bad Request"),
        (401, "Unauthorized"),
        (403, "Forbidden"),
        (500, "Internal Server Error"),
    ],
)
def test_get_http_exception_handles_error(
    photon_get,
    status_code,
    text,
    count_start,
    should_alert,
    sentry_capture_exception,
    redis,
):
    month = get_monthly_timestamp()
    key = f"thumbnail_error:aiohttp.client_exceptions.ClientResponseError:{TEST_IMAGE_DOMAIN}:{month}"
    redis.set(key, count_start)

    with pytest.raises(UpstreamThumbnailException):
        with pook.use():
            pook.get(PHOTON_URL_FOR_TEST_IMAGE).reply(status_code, text).mock
            photon_get(TEST_MEDIA_INFO)

    assert_func = (
        sentry_capture_exception.assert_called_once
        if should_alert
        else sentry_capture_exception.assert_not_called
    )
    assert_func()
    assert redis.get(key) == str(count_start + 1).encode()

    # Assertions about the HTTP error specific message
    assert (
        redis.get(f"thumbnail_http_error:{TEST_IMAGE_DOMAIN}:{month}:{status_code}")
        == b"1"
    )


@pook.on
def test_get_successful_https_image_url_sends_ssl_parameter(
    photon_get, mock_image_data
):
    https_url = TEST_IMAGE_URL.replace("http://", "https://")
    mock_get: pook.Mock = (
        pook.get(PHOTON_URL_FOR_TEST_IMAGE)
        .params(
            {
                "w": settings.THUMBNAIL_WIDTH_PX,
                "quality": settings.THUMBNAIL_QUALITY,
                "ssl": "true",
            }
        )
        .header("User-Agent", UA_HEADER)
        .header("Accept", "image/*")
        .reply(200)
        .body(MOCK_BODY)
        .mock
    )

    https_media_info = replace(TEST_MEDIA_INFO, image_url=https_url)

    res = photon_get(https_media_info)

    assert res.content == MOCK_BODY.encode()
    assert res.status_code == 200
    assert mock_get.matched


@pook.on
def test_get_unsuccessful_request_raises_custom_exception(photon_get):
    mock_get: pook.Mock = pook.get(PHOTON_URL_FOR_TEST_IMAGE).reply(404).mock

    with pytest.raises(
        UpstreamThumbnailException, match=r"Failed to render thumbnail."
    ):
        photon_get(TEST_MEDIA_INFO)

    assert mock_get.matched


@pytest.mark.parametrize(
    "image_url, expected_ext",
    [
        ("example.com/image.jpg", "jpg"),
        ("www.example.com/image.JPG", "jpg"),
        ("http://example.com/image.jpeg", "jpeg"),
        ("https://example.com/image.svg", "svg"),
        ("https://example.com/image.png?foo=1&bar=2#fragment", "png"),
        ("https://example.com/possibleimagewithoutext", ""),
        (
            "https://iip.smk.dk/iiif/jp2/kksgb22133.tif.jp2/full/!400,/0/default.jpg",
            "jpg",
        ),
    ],
)
def test__get_extension_from_url(image_url, expected_ext):
    assert extension._get_file_extension_from_url(image_url) == expected_ext


@pytest.mark.django_db
@pytest.mark.parametrize("image_type", ["apng", "tiff", "bmp"])
def test_photon_get_raises_by_not_allowed_types(photon_get, image_type):
    image_url = TEST_IMAGE_URL.replace(".jpg", f".{image_type}")
    image = ImageFactory.create(url=image_url)
    media_info = MediaInfo(
        media_identifier=image.identifier,
        media_provider=image.provider,
        image_url=image_url,
    )

    with pytest.raises(UnsupportedMediaType):
        photon_get(media_info)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "headers, expected_cache_val",
    [
        ({"Content-Type": "image/tiff"}, b"tiff"),
        ({"Content-Type": "unknown"}, b"unknown"),
    ],
)
def test_photon_get_saves_image_type_to_cache(
    photon_get, redis, headers, expected_cache_val
):
    image_url = TEST_IMAGE_URL.replace(".jpg", "")
    image = ImageFactory.create(url=image_url)
    media_info = MediaInfo(
        media_identifier=image.identifier,
        media_provider=image.provider,
        image_url=image_url,
    )
    with pook.use():
        pook.head(image_url, reply=200, response_headers=headers)
        with pytest.raises(UnsupportedMediaType):
            photon_get(media_info)

        key = f"media:{image.identifier}:thumb_type"
        assert redis.get(key) == expected_cache_val
