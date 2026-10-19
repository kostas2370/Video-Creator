from unittest.mock import Mock, patch

from django.core import signing
from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.services.scenes.jobs import JOB_SALT

from ...baker_recipes import scene, scene_image
from .base import ApiTestCase


class SceneJobTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for(status="COMPLETED")
        self.scene = scene.make(video=self.video)
        self.url = reverse("scene-generate", args=[self.scene.pk])

    def queue(self):
        response = self.client.patch(self.url, {"text": "Rewrite this"}, format="json")
        self.assertEqual(response.status_code, 202, response.data)
        return response.data["id"]

    def run_job(self):
        return self.run_scene_job()

    def test_requests_queue_once_without_running_providers(self):
        with patch("apps.videomanagement.services.scenes.generation.generate_scene") as provider:
            token = self.queue()
            self.assertEqual(self.client.patch(self.url, {"text": "Again"}).status_code, 409)
            provider.assert_not_called()
        self.scene_queue.assert_called_once()
        scene_id, task_id = signing.loads(token, salt=JOB_SALT)
        self.assertEqual(scene_id, str(self.scene.pk))
        self.assertEqual(task_id, self.scene_queue.call_args.kwargs["task_id"])
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "GENERATION")

    def test_worker_returns_rewrite_and_restores_previous_video_status(self):
        self.queue()
        with patch("apps.videomanagement.services.scenes.generation.generate_scene", return_value="A rewrite"):
            self.assertEqual(self.run_job(), {"text": "A rewrite"})
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "COMPLETED")

    def test_polling_uses_celery_results_and_hides_provider_errors(self):
        token = self.queue()
        url = reverse("scene-operation", args=[self.scene.pk])
        for state, expected in (("PENDING", "QUEUED"), ("STARTED", "RUNNING"), ("SUCCESS", "SUCCEEDED"), ("FAILURE", "FAILED")):
            with self.subTest(state=state), patch("apps.videomanagement.services.scenes.jobs.AsyncResult", return_value=Mock(state=state, result={"text": "A rewrite"} if state == "SUCCESS" else RuntimeError("private provider detail"))):
                response = self.client.get(url, {"job": token})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["status"], expected)
                self.assertEqual(response["Cache-Control"], "private, no-store")
                self.assertNotIn("private provider detail", str(response.data))
                if state == "SUCCESS":
                    self.assertEqual(response.data["result"], {"text": "A rewrite"})

    def test_queue_failure_restores_video(self):
        self.scene_queue.side_effect = RuntimeError("Broker unavailable")
        response = self.client.patch(self.url, {"text": "Rewrite"}, format="json")
        self.assertEqual(response.status_code, 503)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "COMPLETED")

    def test_worker_failure_restores_video(self):
        self.queue()
        with patch("apps.videomanagement.services.scenes.generation.generate_scene", side_effect=RuntimeError("Provider unavailable")):
            with self.assertRaises(RuntimeError):
                self.run_job()
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "COMPLETED")

    def test_results_require_owner_matching_scene_and_signed_job_token(self):
        token = self.queue()
        url = reverse("scene-operation", args=[self.scene.pk])
        other_scene = scene.make(video=self.video)
        with patch("apps.videomanagement.services.scenes.jobs.AsyncResult") as result_backend:
            self.assertEqual(self.client.get(reverse("scene-operation", args=[other_scene.pk]), {"job": token}).status_code, 404)
            self.assertEqual(self.client.get(url, {"job": "invalid"}).status_code, 404)
            self.assertEqual(self.client.get(url, {"job": token + "tampered"}).status_code, 404)
            self.assertEqual(self.client.get(url).status_code, 400)
            self.client.force_authenticate(user.make())
            self.assertEqual(self.client.get(url, {"job": token}).status_code, 403)
            self.client.force_authenticate(None)
            self.assertEqual(self.client.get(url, {"job": token}).status_code, 401)
            result_backend.assert_not_called()

    def test_scene_media_changes_and_deletion_are_blocked_while_queued(self):
        image = scene_image.make(scene=self.scene)
        self.queue()
        self.assertEqual(self.client.delete(reverse("video-detail", args=[self.video.pk])).status_code, 409)
        self.assertEqual(self.client.delete(reverse("scene-detail", args=[self.scene.pk])).status_code, 409)
        self.assertEqual(self.client.delete(reverse("sceneimage-detail", args=[image.pk])).status_code, 409)
        self.assertEqual(self.client.post(reverse("scene-change-image-scene", args=[self.scene.pk]), {"with_audio": True}, QUERY_STRING=f"scene_image={image.pk}").status_code, 409)

    def test_visual_provider_failure_keeps_existing_media(self):
        image = scene_image.make(scene=self.scene)
        original_file, original_prompt = image.file.name, image.prompt
        response = self.client.post(reverse("scene-generate-image-scene", args=[self.scene.pk]), {"image_description": "New visual"}, format="json")
        self.assertEqual(response.status_code, 202)
        with patch("apps.videomanagement.services.scenes.visuals.ImageProviderRegistry.resolve", return_value=lambda *args, **kwargs: None):
            with self.assertRaises(RuntimeError):
                self.run_job()
        image.refresh_from_db()
        self.assertEqual(image.file.name, original_file)
        self.assertEqual(image.prompt, original_prompt)

    def test_silent_dialogue_updates_save_without_calling_a_voice_provider(self):
        self.video.settings = {"narration": False}
        self.video.save(update_fields=["settings"])
        response = self.client.patch(reverse("scene-detail", args=[self.scene.pk]), {"text": "New dialogue"}, format="json")
        self.assertEqual(response.status_code, 202)
        with patch("apps.videomanagement.services.scenes.generation.update") as provider:
            self.run_job()
        provider.assert_not_called()
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.text, "New dialogue")
