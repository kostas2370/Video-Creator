import json
from io import StringIO
from unittest.mock import patch

from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from apps.videomanagement import draft_tasks
from apps.videomanagement.baker_recipes import scene, scene_image, voice_model
from apps.videomanagement.services.videos.narration_setup import draft_narration

from .base import ApiTestCase


class NarrationSetupTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for(
            settings={"narration": False, "provider": "gemini-video"},
            voice_model=voice_model.make(),
        )
        self.first = scene.make(video=self.video, text="Camera pans across a bank.")
        self.second = scene.make(video=self.video, text="A borrower signs a form.")
        self.visual = scene_image.make(
            scene=self.first, prompt="A bank counter.", file="existing.mp4"
        )
        self.url = reverse("video-detail", args=[self.video.pk])

    def reviewed(self):
        return [
            {
                "scene_id": str(self.first.pk),
                "before": self.first.text,
                "before_visual": self.visual.prompt,
                "text": "Where does your deposit go?",
            },
            {
                "scene_id": str(self.second.pk),
                "before": self.second.text,
                "before_visual": self.second.text,
                "text": "Banks check whether borrowers can repay.",
            },
        ]

    def test_draft_is_owner_bound_and_only_queues_writing(self):
        response = self.client.post(
            reverse("video-draft-narration", args=[self.video.pk])
        )
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(
            self.draft_queue.call_args.args[0], draft_tasks.draft_narration_task
        )
        other = self.video_for(owner=user.make())
        self.assertEqual(
            self.client.post(
                reverse("video-draft-narration", args=[other.pk])
            ).status_code,
            404,
        )

    def test_generated_draft_is_read_only_and_preserves_original_source_text(self):
        rows = [
            {"scene_id": row["scene_id"], "text": row["text"]}
            for row in self.reviewed()
        ]
        with patch(
            "apps.videomanagement.services.videos.narration_setup.get_reply",
            return_value=StringIO(json.dumps({"scenes": rows})),
        ) as write:
            result = draft_narration(self.video)
        self.first.refresh_from_db()
        self.video.refresh_from_db()
        self.assertEqual(self.first.text, "Camera pans across a bank.")
        self.assertFalse(self.video.settings["narration"])
        self.assertEqual(self.video.status, "READY")
        self.assertEqual(result["scenes"], self.reviewed())
        self.assertIn("never camera", write.call_args.args[0])

    def test_malformed_or_incomplete_ai_drafts_do_not_change_the_project(self):
        from rest_framework.exceptions import ValidationError

        for rows in (
            [],
            [{"scene_id": str(self.first.pk), "text": "Only one"}],
            [{"scene_id": str(self.first.pk), "text": "Duplicate"}] * 2,
        ):
            with (
                self.subTest(rows=rows),
                patch(
                    "apps.videomanagement.services.videos.narration_setup.get_reply",
                    return_value=StringIO(json.dumps({"scenes": rows})),
                ),
            ):
                with self.assertRaises(ValidationError):
                    draft_narration(self.video)
        self.first.refresh_from_db()
        self.assertEqual(self.first.text, "Camera pans across a bank.")

    def test_enabling_requires_review_then_saves_narration_without_changing_visuals(
        self,
    ):
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay"
        ) as speech:
            self.assertEqual(
                self.client.patch(self.url, {"narration": True}).status_code, 400
            )
            speech.assert_not_called()
            response = self.client.patch(
                self.url,
                {"narration": True, "narration_scenes": self.reviewed()},
                format="json",
            )
        self.assertEqual(response.status_code, 202, response.data)
        speech.assert_called_once()
        self.first.refresh_from_db()
        self.visual.refresh_from_db()
        self.assertEqual(self.first.text, "Where does your deposit go?")
        self.assertEqual(self.visual.prompt, "A bank counter.")
        self.assertEqual(self.visual.file.name, "existing.mp4")

    def test_stale_text_visuals_or_scene_order_reject_the_entire_review(self):
        for variant in ("text", "visual", "order", "missing", "duplicate"):
            rows = self.reviewed()
            if variant == "text":
                rows[1]["before"] = "Stale"
            if variant == "visual":
                rows[1]["before_visual"] = "Stale visual"
            if variant == "order":
                rows.reverse()
            if variant == "missing":
                rows.pop()
            if variant == "duplicate":
                rows[1] = rows[0]
            with (
                self.subTest(variant=variant),
                patch(
                    "apps.videomanagement.tasks.regenerate_narration_task.delay"
                ) as speech,
            ):
                response = self.client.patch(
                    self.url,
                    {"narration": True, "narration_scenes": rows},
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
                speech.assert_not_called()
            self.first.refresh_from_db()
            self.video.refresh_from_db()
            self.assertEqual(self.first.text, "Camera pans across a bank.")
            self.assertFalse(self.video.settings["narration"])

    def test_queue_failure_rolls_back_reviewed_text_too(self):
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay",
            side_effect=RuntimeError("offline"),
        ):
            response = self.client.patch(
                self.url,
                {"narration": True, "narration_scenes": self.reviewed()},
                format="json",
            )
        self.assertEqual(response.status_code, 503)
        self.first.refresh_from_db()
        self.assertEqual(self.first.text, "Camera pans across a bank.")

    def test_audio_mix_settings_do_not_regenerate_media(self):
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay"
        ) as speech:
            response = self.client.patch(
                self.url,
                {
                    "video_audio_mode": "DIALOGUE",
                    "video_audio_enabled": True,
                    "music_volume": 0,
                },
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)
        speech.assert_not_called()
        self.visual.refresh_from_db()
        self.video.refresh_from_db()
        self.assertTrue(self.visual.with_audio)
        self.assertEqual(self.video.settings["music_volume"], 0)
        self.assertEqual(self.video.settings["video_audio_mode"], "DIALOGUE")
