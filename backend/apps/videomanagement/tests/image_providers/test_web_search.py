from unittest.mock import patch

from django.test import SimpleTestCase

from ...utils.image_providers import (
    bing,
    google_images,
)
from ...utils.image_providers.bing import download_image
from ...utils.image_providers.google_images import download_image_from_google


class DownloadImageTests(SimpleTestCase):
    def test_returns_the_first_result_from_bing(self):
        with patch.object(bing.downloader, "download", return_value=(["a.png"], 1)):
            self.assertEqual(download_image("a cat", "images/"), ["a.png"])

    def test_returns_nothing_when_bing_fails_rather_than_breaking_the_scene(self):
        with patch.object(
            bing.downloader, "download", side_effect=RuntimeError("no results")
        ):
            self.assertIsNone(download_image("a cat", "images/"))

    def test_returns_the_google_result(self):
        with patch.object(google_images, "download", return_value="a.png"):
            self.assertEqual(download_image_from_google("a cat", "images/"), "a.png")

    def test_returns_nothing_when_google_fails(self):
        with patch.object(google_images, "download", side_effect=RuntimeError("429")):
            self.assertIsNone(download_image_from_google("a cat", "images/"))
