"""Every provider call is stubbed: no OpenAI, Bing or Google request is made."""

import base64
import os
import tempfile
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import APIException

from ..utils.image_providers import (
    bing,
    diffusion,
    google_images,
    midjourney,
    openai_images,
    sora,
)
from ..utils.image_providers.bing import download_image
from ..utils.image_providers.google_images import download_image_from_google
from ..utils.image_providers.openai_images import generate_from_dalle
from ..utils.image_providers.sora import generate_from_sora


class GenerateFromSoraTests(SimpleTestCase):
    def setUp(self):
        self.video = MagicMock(status="completed", id="vid_1")
        self.client = MagicMock()
        self.client.videos.create_and_poll.return_value = self.video
        patcher = patch.object(sora, "OpenAI", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def generate(self, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            kwargs.setdefault("prompt", "a cat naps")
            kwargs.setdefault("dir_name", f"{tmp}/")
            return generate_from_sora(**kwargs)

    def requested_seconds(self, duration):
        self.generate(duration=duration)
        return self.client.videos.create_and_poll.call_args.kwargs["seconds"]

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_asks_for_the_shortest_clip_that_covers_the_narration(self):
        self.assertEqual(self.requested_seconds(3.0), "4")
        self.assertEqual(self.requested_seconds(5.0), "8")
        self.assertEqual(self.requested_seconds(9.0), "12")

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_caps_a_long_sentence_at_the_longest_clip_sora_renders(self):
        # handle_video covers the rest by holding the final frame.
        self.assertEqual(self.requested_seconds(30.0), "12")

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_falls_back_to_the_silent_scene_length_with_no_narration_to_fit(self):
        # Not the 4s minimum: a silent scene would otherwise collapse by accident.
        self.assertEqual(self.requested_seconds(0), "8")

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7, SORA_STYLE="noir")
    def test_carries_the_shared_style_into_every_shot(self):
        self.generate(duration=4.0, title="Cats")

        prompt = self.client.videos.create_and_poll.call_args.kwargs["prompt"]
        self.assertIn("noir", prompt)
        self.assertIn("a cat naps", prompt)

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_anchors_the_shot_to_a_reference_frame_when_one_exists(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as anchor:
            self.generate(duration=4.0, reference=anchor.name)

        self.assertIn(
            "input_reference", self.client.videos.create_and_poll.call_args.kwargs
        )

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_ignores_a_reference_frame_that_is_not_on_disk(self):
        self.generate(duration=4.0, reference="/nowhere/anchor.png")

        self.assertNotIn(
            "input_reference", self.client.videos.create_and_poll.call_args.kwargs
        )

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_raises_with_the_providers_reason_when_the_job_does_not_complete(self):
        self.video.status = "failed"
        self.video.error = MagicMock(code="moderation", message="blocked")

        with self.assertRaises(APIException) as caught:
            self.generate(duration=4.0)

        self.assertIn("moderation", str(caught.exception))

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_writes_the_finished_clip_as_an_mp4(self):
        path = self.generate(duration=4.0)

        self.assertTrue(path.endswith(".mp4"))
        self.client.videos.download_content.assert_called_once()


class GenerateFromDalleTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.client = MagicMock()
        self.client.images.generate.return_value.data = [
            MagicMock(b64_json=base64.b64encode(b"a png").decode())
        ]
        patcher = patch.object(openai_images, "OpenAI", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    @override_settings(
        OPEN_API_KEY="key",
        IMAGE_MODEL="gpt-image-1",
        IMAGE_SIZE="1024x1024",
        IMAGE_QUALITY="high",
    )
    def test_decodes_the_image_to_a_png(self):
        path = generate_from_dalle("a cat", f"{self.tmp.name}/", style="vivid")

        self.assertTrue(path.endswith(".png"))
        self.assertEqual(open(path, "rb").read(), b"a png")

    @override_settings(
        OPEN_API_KEY="key",
        IMAGE_MODEL="gpt-image-1",
        IMAGE_SIZE="1024x1024",
        IMAGE_QUALITY="high",
    )
    def test_folds_the_style_into_the_prompt(self):
        # gpt-image has no `style` argument — that was DALL-E 3 only.
        generate_from_dalle("a cat", f"{self.tmp.name}/", style="vivid", title="Cats")

        kwargs = self.client.images.generate.call_args.kwargs
        self.assertIn("Style: vivid", kwargs["prompt"])
        self.assertNotIn("style", kwargs)

    @override_settings(
        OPEN_API_KEY="key",
        IMAGE_MODEL="gpt-image-1",
        IMAGE_SIZE="1024x1024",
        IMAGE_QUALITY="high",
    )
    def test_raises_when_the_model_returns_no_image(self):
        self.client.images.generate.return_value.data = []

        with self.assertRaises(APIException):
            generate_from_dalle("a cat", f"{self.tmp.name}/", style="vivid")


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
