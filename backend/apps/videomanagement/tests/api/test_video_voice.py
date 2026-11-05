from unittest.mock import patch

from django.urls import reverse

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import avatar, scene, voice_model
from .base import ApiTestCase


class VideoVoiceTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user.use_service_api_keys = False
        self.user.save(update_fields=["use_service_api_keys"])
        self.video = self.video_for(avatar=None)
        self.voice = voice_model.make(created_by=self.user, type="CUSTOM_API")
        self.url = reverse("video-detail", args=[self.video.pk])

    def test_changes_voice_and_regenerates_each_scene_without_an_avatar(self):
        scene.make(video=self.video, _quantity=2)
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay"
        ) as narrate:
            response = self.client.patch(
                self.url, {"voice_id": str(self.voice.pk)}, format="json"
            )
        self.assertEqual(response.status_code, 202, response.data)
        self.video.refresh_from_db()
        self.assertEqual(self.video.voice_model_id, self.voice.pk)
        self.assertEqual(response.data["video"]["voice_model"], self.voice.pk)
        narrate.assert_called_once()
        self.assertEqual(self.video.status, "GENERATION")
        from apps.videomanagement.tasks import regenerate_narration_task

        with patch("apps.videomanagement.tasks.regenerate_scene_narration") as speech:
            regenerate_narration_task.run(*narrate.call_args.args)
        self.assertEqual(speech.call_count, 2)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "READY")

    def test_does_not_regenerate_when_voice_is_unchanged_or_narration_is_off(self):
        self.video.voice_model = self.voice
        self.video.save(update_fields=["voice_model"])
        scene.make(video=self.video)
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay"
        ) as narrate:
            self.assertEqual(
                self.client.patch(
                    self.url, {"voice_id": str(self.voice.pk)}
                ).status_code,
                200,
            )
            self.video.settings = {"narration": False}
            self.video.save(update_fields=["settings"])
            other = voice_model.make(created_by=self.user, type="CUSTOM_API")
            self.assertEqual(
                self.client.patch(self.url, {"voice_id": str(other.pk)}).status_code,
                200,
            )
        narrate.assert_not_called()
        self.video.refresh_from_db()
        self.assertEqual(self.video.voice_model_id, other.pk)

    def test_rejects_foreign_voice_before_changing_other_fields(self):
        foreign = voice_model.make(created_by=user.make(), type="CUSTOM_API")
        original = self.video.voice_model_id, self.video.title
        response = self.client.patch(
            self.url, {"voice_id": str(foreign.pk), "title": "Changed"}
        )
        self.assertEqual(response.status_code, 404)
        self.video.refresh_from_db()
        self.assertEqual((self.video.voice_model_id, self.video.title), original)

    def test_avatar_voice_cannot_be_overridden(self):
        self.video.avatar = avatar.make(created_by=self.user)
        self.video.save(update_fields=["avatar"])
        response = self.client.patch(self.url, {"voice_id": str(self.voice.pk)})
        self.assertEqual(response.status_code, 400)
        self.assertIn("voice_id", response.data)

    def test_can_choose_voice_when_removing_avatar(self):
        self.video.avatar = avatar.make(created_by=self.user)
        self.video.save(update_fields=["avatar"])
        with patch("apps.videomanagement.tasks.regenerate_narration_task.delay"):
            response = self.client.patch(
                self.url, {"avatar": "", "voice_id": str(self.voice.pk)}
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.video.refresh_from_db()
        self.assertIsNone(self.video.avatar_id)
        self.assertEqual(self.video.voice_model_id, self.voice.pk)

    def test_rejects_voice_changes_while_processing_and_invalid_voice_ids(self):
        for value in ("", None, "invalid"):
            self.assertEqual(
                self.client.patch(
                    self.url, {"voice_id": value}, format="json"
                ).status_code,
                400,
            )
        self.video.status = "GENERATION"
        self.video.save(update_fields=["status"])
        self.assertEqual(
            self.client.patch(self.url, {"voice_id": str(self.voice.pk)}).status_code,
            409,
        )

    def test_queue_failure_rolls_back_voice_title_and_status(self):
        scene.make(video=self.video)
        original = self.video.voice_model_id, self.video.title, self.video.status
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay",
            side_effect=RuntimeError("broker unavailable"),
        ):
            response = self.client.patch(
                self.url, {"voice_id": str(self.voice.pk), "title": "Changed"}
            )
        self.assertEqual(response.status_code, 503)
        self.video.refresh_from_db()
        self.assertEqual(
            (self.video.voice_model_id, self.video.title, self.video.status), original
        )

    def test_failed_narration_unlocks_project_and_can_be_queued_again(self):
        from apps.videomanagement.tasks import regenerate_narration_task

        scene.make(video=self.video)
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay"
        ) as queue:
            response = self.client.patch(self.url, {"voice_id": str(self.voice.pk)})
        self.assertEqual(response.status_code, 202)
        with patch(
            "apps.videomanagement.tasks.regenerate_scene_narration",
            side_effect=RuntimeError("provider unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                regenerate_narration_task.run(*queue.call_args.args)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay"
        ) as queue:
            response = self.client.patch(self.url, {"voice_id": str(self.voice.pk)})
        self.assertEqual(response.status_code, 202)
        with patch("apps.videomanagement.tasks.regenerate_scene_narration"):
            regenerate_narration_task.run(*queue.call_args.args)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "READY")
