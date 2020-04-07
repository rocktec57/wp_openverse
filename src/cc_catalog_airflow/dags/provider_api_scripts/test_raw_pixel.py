import json
import logging
import os

from unittest.mock import patch

import raw_pixel as rwp

RESOURCES = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "tests/resources/rawpixel"
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s:  %(message)s",
    level=logging.DEBUG,
)


def _get_resource_json(json_name):
    with open(os.path.join(RESOURCES, json_name)) as f:
        resource_json = json.load(f)
    return resource_json


def test_get_image_list_giving_none():
    with patch.object(rwp, "_request_content", return_value=None):
        total, result = rwp._get_image_list()
        assert total is None
        assert result is None


def test_get_image_list_correct():
    r = _get_resource_json("total_images_example.json")
    with patch.object(rwp, "_request_content", return_value=r):
        total, result = rwp._get_image_list()
        assert total == 22215
        assert len(result) == 1


def test_process_pages_giving_zero():
    with patch.object(rwp, "_request_content", return_value=None):
        total, result = rwp._get_image_list()
        img_ctr = rwp._process_pages(total, result, page=1)
        assert img_ctr == 0


def test_process_image_data():
    r = _get_resource_json("total_images_example.json")
    with patch.object(rwp, "_request_content", return_value=r):
        result = rwp._get_image_list()[1]
        assert rwp._process_image_data(image=result[0]) == 1


def test_get_foreign_id_url():
    r = _get_resource_json("total_images_example.json")
    with patch.object(rwp, "_request_content", return_value=r):
        result = rwp._get_image_list()[1]
        foreign_id, foreign_url = rwp._get_foreign_id_url(image=result[0])
        assert foreign_id == 2041320
        assert (
            foreign_url
            == "https://www.rawpixel.com/image/2041320/world-map-drawn-oval-projection"
        )


def test_get_image_properties():
    r = _get_resource_json("total_images_example.json")
    with patch.object(rwp, "_request_content", return_value=r):
        result = rwp._get_image_list()[1]
        img_url, width, height, thumbnail = rwp._get_image_properties(
            image=result[0], foreign_url=""
        )
        assert (
            img_url
            == "https://img.rawpixel.com/s3fs-private/rawpixel_images/website_content/pdmaps-loc-06-nam_1.jpg?w=1200&h=630&fit=crop&dpr=1.5&crop=entropy&fm=pjpg&q=75&vib=3&con=3&usm=15&markpad=13&markalpha=90&markscale=10&markx=25&mark=rawpixel-watermark.png&cs=srgb&bg=F4F4F3&ixlib=js-2.2.1&s=edbf5b420430b7f118a0093686c40f93"
        )
        assert width == "1200"
        assert height == "630"
        assert (
            thumbnail
            == "https://img.rawpixel.com/s3fs-private/rawpixel_images/website_content/pdmaps-loc-06-nam_1.jpg?w=400&dpr=1&fit=default&crop=default&auto=format&fm=pjpg&q=75&vib=3&con=3&usm=15&bg=F4F4F3&ixlib=js-2.2.1&s=6f33bfab36227436a0f9ad230fc1d64a"
        )


def test_get_title_owner():
    r = _get_resource_json("total_images_example.json")
    with patch.object(rwp, "_request_content", return_value=r):
        result = rwp._get_image_list()[1]
        title, owner = rwp._get_title_owner(image=result[0])
        assert title == "World map drawn on an oval projection"
        assert owner == "Library of Congress"


def test_get_tags():
    r = _get_resource_json("total_images_example.json")
    with patch.object(rwp, "_request_content", return_value=r):
        result = rwp._get_image_list()[1]
        tags = rwp._get_tags(image=result[0])
        assert len(tags) == 47
        assert tags[0] == {"name": "america", "provider": "rawpixel"}
