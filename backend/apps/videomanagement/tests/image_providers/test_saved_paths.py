import os
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ...utils.image_providers import (
    diffusion,
    google_images,
    midjourney,
)


class SavedPathTests(SimpleTestCase):
    DIR = "media/videos/a video/images/"

    def assert_saved_into_the_directory(self, saved):
        self.assertNotIn("\\", saved)
        self.assertEqual(os.path.dirname(saved), self.DIR.rstrip("/"))

    def test_diffusion_saves_into_the_directory_it_was_given(self):
        response = MagicMock()
        response.json.return_value = {"output": ["https://img.test/a.png"]}

        with (
            patch.object(diffusion.requests, "post", return_value=response),
            patch.object(diffusion.urllib.request, "urlretrieve") as retrieve,
        ):
            saved = diffusion.generate_from_diffusion("a cat", self.DIR)

        self.assert_saved_into_the_directory(saved)
        self.assertEqual(retrieve.call_args.args[1], saved)

    def test_midjourney_saves_into_the_directory_it_was_given(self):
        queued = MagicMock()
        queued.json.return_value = {"success": True, "messageId": "m1"}
        finished = MagicMock()
        finished.json.return_value = {"uri": "https://img.test/a.png"}

        with (
            patch.object(midjourney.requests, "post", return_value=queued),
            patch.object(midjourney.requests, "get", return_value=finished),
            patch.object(midjourney.urllib.request, "urlretrieve") as retrieve,
        ):
            saved = midjourney.generate_from_midjourney("a cat", self.DIR)

        self.assert_saved_into_the_directory(saved)
        self.assertEqual(retrieve.call_args.args[1], saved)

    def test_google_saves_into_the_directory_it_was_given(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"items": [{"link": "https://img.test/a.jpg"}]}

        with (
            patch.object(google_images, "make_request", return_value=response),
            patch.object(google_images.urllib.request, "urlretrieve") as retrieve,
        ):
            saved = google_images.download("a cat", path=self.DIR)

        self.assert_saved_into_the_directory(saved)
        self.assertEqual(retrieve.call_args.args[1], saved)
