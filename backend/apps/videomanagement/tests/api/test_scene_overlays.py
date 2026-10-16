import io
import json
import tempfile

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from ...baker_recipes import scene
from .base import ApiTestCase


class SceneOverlayTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for(status="READY")
        self.scene = scene.make(video=self.video)
        self.url = reverse("scene-overlays", args=[self.scene.pk])
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)

    def test_save_clear_and_preview_without_generating_media(self):
        response = self.client.patch(
            self.url,
            {"overlays": [{"kind": "title", "text": "Hello", "start": 0.2, "end": 2}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["overlays"][0]["text"], "Hello")
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.overlays[0]["position"], "middle-center")
        preview = self.client.get(reverse("video-preview", args=[self.video.pk]))
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data["segments"][0]["overlays"], self.scene.overlays)
        response = self.client.patch(self.url, {"overlays": []}, format="json")
        self.assertEqual(response.status_code, 200)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.overlays, [])
        self.scene_queue.assert_not_called()

    def test_multipart_logo_and_json_settings_are_saved_together(self):
        buffer = io.BytesIO()
        Image.new("RGBA", (32, 32), "red").save(buffer, format="PNG")
        response = self.client.patch(
            self.url,
            {
                "overlays": json.dumps([{"kind": "watermark", "logo": True}]),
                "overlay_logo": SimpleUploadedFile(
                    "logo.png", buffer.getvalue(), content_type="image/png"
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["overlay_logo"])
        self.assertTrue(response.data["overlays"][0]["logo"])
        self.scene.refresh_from_db()
        self.assertTrue(
            self.scene.overlay_logo.storage.exists(self.scene.overlay_logo.name)
        )

    def test_rejects_bad_settings(self):
        for overlays in (
            [{"kind": "title", "text": "Hello", "start": 2, "end": 1}],
            [{"kind": "title", "text": "Hello", "start": -1}],
            [{"kind": "title", "text": "Hello", "size": 100}],
            [{"kind": "title", "text": "Hello", "color": "red:injected"}],
            [{"kind": "title", "text": "Hello", "position": "outside"}],
            [{"kind": "title", "text": "   "}],
            [{"kind": "watermark", "logo": True}],
            [{"kind": "title", "text": "Hello"}] * 9,
        ):
            response = self.client.patch(
                self.url, {"overlays": overlays}, format="json"
            )
            self.assertEqual(response.status_code, 400, response.data)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.overlays, [])

    def test_ownership_and_processing_lock(self):
        other = scene.make(video=self.video_for(owner=user.make(), status="READY"))
        response = self.client.patch(
            reverse("scene-overlays", args=[other.pk]), {"overlays": []}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.video.status = "RENDERING"
        self.video.save()
        response = self.client.patch(
            self.url,
            {"overlays": [{"kind": "cta", "text": "Click here"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.overlays, [])
