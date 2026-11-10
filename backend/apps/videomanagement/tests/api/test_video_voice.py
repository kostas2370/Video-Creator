from unittest.mock import patch

from django.urls import reverse

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import avatar, scene, voice_model
from apps.videomanagement.tasks import regenerate_narration_task
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
        with patch("apps.videomanagement.tasks.regenerate_scene_narration") as speech:
            regenerate_narration_task.run(
                *narrate.call_args.args, **narrate.call_args.kwargs
            )
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

    def test_enabling_narration_queues_speech_with_the_existing_voice(self):
        self.video.settings = {"narration": False, "provider": "gemini-video"}
        self.video.voice_model = self.voice
        self.video.save(update_fields=["settings", "voice_model"])
        line = scene.make(video=self.video, text="Read this aloud.")
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay"
        ) as queue:
            response = self.client.patch(
                self.url,
                {
                    "narration": True,
                    "narration_scenes": [
                        {
                            "scene_id": str(line.pk),
                            "before": line.text,
                            "before_visual": line.text,
                            "text": line.text,
                        }
                    ],
                },
                format="json",
            )
        self.assertEqual(response.status_code, 202, response.data)
        self.video.refresh_from_db()
        self.assertTrue(self.video.settings["narration"])
        self.assertEqual(self.video.settings["provider"], "gemini-video")
        self.assertEqual(self.video.status, "GENERATION")
        queue.assert_called_once()
        with patch("apps.videomanagement.tasks.regenerate_scene_narration") as speech:
            regenerate_narration_task.run(
                *queue.call_args.args, **queue.call_args.kwargs
            )
        self.assertEqual(speech.call_args.args[0].pk, line.pk)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "READY")
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay"
        ) as queue:
            self.assertEqual(
                self.client.patch(self.url, {"narration": True}).status_code, 200
            )
        queue.assert_not_called()

    def test_disabling_narration_preserves_recordings_without_queuing_speech(self):
        line = scene.make(video=self.video, file="speech/saved.wav")
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay"
        ) as queue:
            response = self.client.patch(self.url, {"narration": False})
        self.assertEqual(response.status_code, 200, response.data)
        self.video.refresh_from_db()
        line.refresh_from_db()
        self.assertFalse(self.video.settings["narration"])
        self.assertEqual(line.file.name, "speech/saved.wav")
        queue.assert_not_called()

    def test_enabling_narration_without_a_voice_is_rejected(self):
        self.video.settings = {"narration": False}
        self.video.voice_model = None
        self.video.save(update_fields=["settings", "voice_model"])
        response = self.client.patch(self.url, {"narration": True})
        self.assertEqual(response.status_code, 400)
        self.assertIn("voice_id", response.data)
        self.video.refresh_from_db()
        self.assertFalse(self.video.settings["narration"])

    def test_enabling_narration_rolls_back_when_queue_is_unavailable(self):
        self.video.settings = {"narration": False}
        self.video.voice_model = self.voice
        self.video.save(update_fields=["settings", "voice_model"])
        line = scene.make(video=self.video)
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay",
            side_effect=RuntimeError("offline"),
        ):
            response = self.client.patch(
                self.url,
                {
                    "narration": True,
                    "narration_scenes": [
                        {
                            "scene_id": str(line.pk),
                            "before": line.text,
                            "before_visual": line.text,
                            "text": "New spoken narration.",
                        }
                    ],
                },
                format="json",
            )
        self.assertEqual(response.status_code, 503)
        self.video.refresh_from_db()
        self.assertFalse(self.video.settings["narration"])
        self.assertEqual(self.video.status, "READY")

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
                regenerate_narration_task.run(
                    *queue.call_args.args, **queue.call_args.kwargs
                )
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay"
        ) as queue:
            response = self.client.patch(self.url, {"retry_narration": True})
        self.assertEqual(response.status_code, 202)
        with patch("apps.videomanagement.tasks.regenerate_scene_narration"):
            regenerate_narration_task.run(
                *queue.call_args.args, **queue.call_args.kwargs
            )
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "READY")

    def test_unrelated_settings_do_not_retry_failed_generation(self):
        self.video.voice_model = self.voice
        self.video.status = "FAILED"
        self.video.save(update_fields=["voice_model", "status"])
        scene.make(video=self.video)
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay"
        ) as queue:
            response = self.client.patch(
                self.url, {"voice_id": str(self.voice.pk), "caption_style": "TIKTOK"}
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["video"]["can_retry_narration"])
        queue.assert_not_called()
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")
        self.assertEqual(self.video.settings["caption_style"], "TIKTOK")

    def test_explicit_retry_rejects_unrelated_project_failures(self):
        self.video.status = "FAILED"
        self.video.save(update_fields=["status"])
        response = self.client.patch(
            self.url, {"retry_narration": True, "title": "Changed"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("retry_narration", response.data)
        self.video.refresh_from_db()
        self.assertNotEqual(self.video.title, "Changed")

    def test_changing_voice_does_not_clear_an_unrelated_generation_failure(self):
        self.video.status = "FAILED"
        self.video.save(update_fields=["status"])
        scene.make(video=self.video)
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay"
        ) as queue:
            response = self.client.patch(self.url, {"voice_id": str(self.voice.pk)})
        self.assertEqual(response.status_code, 202)
        with patch("apps.videomanagement.tasks.regenerate_scene_narration"):
            regenerate_narration_task.run(
                *queue.call_args.args, **queue.call_args.kwargs
            )
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")
        self.assertEqual(self.video.narration_retry_status, "")

    def test_resume_cannot_skip_a_failed_voice_change(self):
        self.video.status = "FAILED"
        self.video.narration_retry_status = "READY"
        self.video.save(update_fields=["status", "narration_retry_status"])
        with patch("apps.videomanagement.tasks.resume_video_task.delay") as queue:
            response = self.client.patch(reverse("video-resume", args=[self.video.pk]))
        self.assertEqual(response.status_code, 409, response.data)
        queue.assert_not_called()
