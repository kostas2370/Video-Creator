import tempfile
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import APIException

from ...utils.image_providers import (
    sora,
)
from ...utils.image_providers.sora import generate_from_sora


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
