from unittest.mock import patch

from django.test import SimpleTestCase

from apps.videomanagement.integrations.visuals import bing, google_images
from apps.videomanagement.integrations.visuals.bing import BingImageProvider
from apps.videomanagement.integrations.visuals.google_images import (
    GoogleImageProvider,
)


class DownloadImageTests(SimpleTestCase):
    def test_returns_the_first_result_from_bing(self):
        with patch.object(bing.downloader, "download", return_value=(["a.png"], 1)):
            self.assertEqual(BingImageProvider.generate("a cat", "images/"), ["a.png"])

    def test_returns_nothing_when_bing_fails_rather_than_breaking_the_scene(self):
        with patch.object(
            bing.downloader, "download", side_effect=RuntimeError("no results")
        ):
            self.assertIsNone(BingImageProvider.generate("a cat", "images/"))

    def test_returns_the_google_result(self):
        with patch.object(google_images, "download", return_value="a.png"):
            self.assertEqual(GoogleImageProvider.generate("a cat", "images/"), "a.png")

    def test_returns_nothing_when_google_fails(self):
        with patch.object(google_images, "download", side_effect=RuntimeError("429")):
            self.assertIsNone(GoogleImageProvider.generate("a cat", "images/"))
