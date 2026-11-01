import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import scene, scene_image
from apps.videomanagement.services.scenes.visuals import create_image_scene

from .base import ApiTestCase


class StartingImageTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        storage = override_settings(MEDIA_ROOT=self.tmp.name)
        storage.enable()
        self.addCleanup(storage.disable)
        output = BytesIO()
        Image.new("RGB", (32, 32), "blue").save(output, format="PNG")
        self.png = output.getvalue()
        self.frame = Path(self.tmp.name, "start.png")
        self.frame.write_bytes(self.png)
        Path(self.tmp.name, "cast.png").write_bytes(self.png)
        self.video = self.video_for(
            mode="AI",
            status="READY",
            reference_image="cast.png",
            settings={
                "provider": "kling",
                "character_references": True,
                "narration": False,
            },
        )
        self.scene = scene.make(video=self.video)
        self.old = scene_image.make(
            scene=self.scene, file="images/old.mp4", prompt="Old shot"
        )
        self.url = reverse("scene-starting-image", args=[self.scene.pk])
        with patch(
            "apps.videomanagement.services.scenes.visuals.openai_images.generate_openai_image",
            return_value=str(self.frame),
        ):
            create_image_scene(
                self.video,
                "Milo at gate",
                self.scene.text,
                self.video.dir_name,
                scene=self.scene,
                mode="AI",
                provider="kling",
                user=self.user,
            )
        self.scene.refresh_from_db()

    def post(self, operation, **extra):
        return self.client.post(
            self.url,
            {
                "operation": operation,
                "asset_id": str(self.scene.starting_asset_id),
                **extra,
            },
            format="json",
        )

    def test_approval_and_animation_are_separate_and_worker_uses_saved_image(self):
        self.assertEqual(self.post("animate").status_code, 400)
        approved = self.post("approve")
        self.assertEqual(approved.status_code, 200, approved.data)
        self.assertEqual(approved.data["starting_image_status"], "approved")
        self.scene_queue.assert_not_called()
        response = self.post("animate")
        self.assertEqual(response.status_code, 202, response.data)
        provider = Mock(return_value="images/new.mp4")
        with patch(
            "apps.videomanagement.services.scenes.starting_images.ImageProviderRegistry.resolve",
            return_value=provider,
        ):
            self.run_scene_job()
        self.assertEqual(
            provider.call_args.kwargs["reference"], self.scene.starting_asset.file.path
        )
        self.old.refresh_from_db()
        self.assertEqual(self.old.file.name, "images/new.mp4")

    def test_failure_restores_editing_and_keeps_clip_and_approved_image_for_retry(self):
        self.post("approve")
        self.post("animate")
        with patch(
            "apps.videomanagement.services.scenes.starting_images.ImageProviderRegistry.resolve",
            side_effect=RuntimeError("private upstream details"),
        ):
            with self.assertRaises(RuntimeError):
                self.run_scene_job()
        self.video.refresh_from_db()
        self.scene.refresh_from_db()
        self.old.refresh_from_db()
        self.assertEqual(self.video.status, "READY")
        self.assertEqual(self.old.file.name, "images/old.mp4")
        self.assertIn(
            "Animation failed", self.scene.starting_image_context["animation_error"]
        )
        self.assertNotIn("private upstream", str(self.scene.starting_image_context))
        self.assertEqual(self.post("animate").status_code, 202)

    def test_upload_requires_review_and_preserves_current_clip(self):
        self.post("approve")
        response = self.client.post(
            self.url,
            {
                "operation": "upload",
                "asset_id": str(self.scene.starting_asset_id),
                "image_description": "Milo in workshop",
                "image": SimpleUploadedFile(
                    "replacement.png", self.png, content_type="image/png"
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["starting_image_status"], "needs_review")
        self.assertEqual(
            response.data["starting_image_description"], "Milo in workshop"
        )
        self.old.refresh_from_db()
        self.assertEqual(self.old.file.name, "images/old.mp4")
        self.scene_queue.assert_not_called()

    def test_invalid_upload_and_stale_approval_are_rejected(self):
        self.assertEqual(self.post("approve", asset_id=str(uuid4())).status_code, 400)
        response = self.client.post(
            self.url,
            {
                "operation": "upload",
                "asset_id": str(self.scene.starting_asset_id),
                "image": SimpleUploadedFile(
                    "fake.png", b"not an image", content_type="image/png"
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.scene_queue.assert_not_called()

    def test_other_users_and_busy_projects_cannot_change_approval(self):
        self.client.force_authenticate(user.make())
        self.assertEqual(self.post("approve").status_code, 403)
        self.client.force_authenticate(self.user)
        self.video.status = "RENDERING"
        self.video.save(update_fields=["status"])
        self.assertEqual(self.post("approve").status_code, 409)

    def test_worker_rechecks_approval_before_calling_a_paid_provider(self):
        self.post("approve")
        self.post("animate")
        self.scene.starting_image_context = {
            **self.scene.starting_image_context,
            "approved_asset": "stale",
        }
        self.scene.save(update_fields=["starting_image_context"])
        with patch(
            "apps.videomanagement.services.scenes.starting_images.ImageProviderRegistry.resolve"
        ) as provider:
            with self.assertRaises(Exception):
                self.run_scene_job()
        provider.assert_not_called()
