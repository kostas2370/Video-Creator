import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.models import MediaAsset, Scene, SceneImage
from apps.videomanagement.tasks import generate_cover_task

from .base import ApiTestCase


class VisualArchivingTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.media_root = Path(directory.name)
        self.video = self.video_for(status="READY", video_type="MANUAL")

    def image(self, color="blue"):
        output = BytesIO()
        Image.new("RGB", (64, 64), color).save(output, format="PNG")
        return SimpleUploadedFile(
            "image.png", output.getvalue(), content_type="image/png"
        )

    def request(self, method, *args, **kwargs):
        with self.captureOnCommitCallbacks(execute=True):
            return getattr(self.client, method)(*args, **kwargs)

    def make_visual(self):
        with self.captureOnCommitCallbacks(execute=True):
            scene = Scene.objects.create(video=self.video, text="Scene one")
            visual = SceneImage.objects.create(scene=scene, file=self.image())
        return visual

    def test_scene_regeneration_keeps_independent_versions_after_video_deletion(self):
        visual = self.make_visual()
        first = visual.asset
        self.assertEqual(first.created_by_id, self.user.pk)
        self.assertEqual(first.source_video_id, self.video.pk)
        self.assertIn("scene image", first.tags)
        self.assertNotEqual(first.file.name, visual.file.name)
        first_bytes = first.file.read()
        with self.captureOnCommitCallbacks(execute=True):
            visual.file = self.image("red")
            visual.save()
        second = MediaAsset.objects.get(pk=visual.asset_id)
        self.assertNotEqual(first.pk, second.pk)
        with first.file.open("rb") as saved:
            self.assertEqual(saved.read(), first_bytes)
        with self.captureOnCommitCallbacks(execute=True):
            self.video.delete()
        self.assertEqual(MediaAsset.objects.count(), 2)
        for asset in MediaAsset.objects.all():
            self.assertIsNone(asset.source_video_id)
            self.assertTrue(asset.file.storage.exists(asset.file.name))

    def test_library_reuse_and_duplicate_upload_do_not_duplicate_assets(self):
        endpoint = reverse("mediaasset-list")
        first = self.request(
            "post",
            endpoint,
            {"title": "Original", "file": self.image()},
            format="multipart",
        )
        second = self.request(
            "post",
            endpoint,
            {"title": "Again", "file": self.image()},
            format="multipart",
        )
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.data["id"], first.data["id"])
        result = self.request(
            "post",
            reverse("mediaasset-use", args=[first.data["id"]]),
            {"video_id": str(self.video.pk), "purpose": "new_scene", "duration": 3},
            format="json",
        )
        self.assertEqual(result.status_code, 200, result.data)
        visual = self.video.scenes.get().scene_images.get()
        self.assertEqual(str(visual.asset_id), str(first.data["id"]))
        self.assertEqual(MediaAsset.objects.count(), 1)
        original_file = visual.file.name
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(
                self.request(
                    "delete", reverse("mediaasset-detail", args=[first.data["id"]])
                ).status_code,
                204,
            )
        visual.refresh_from_db()
        self.assertIsNone(visual.asset_id)
        self.assertEqual(visual.file.name, original_file)
        self.assertTrue(visual.file.storage.exists(original_file))
        visual.with_audio = False
        visual.save(update_fields=["with_audio"])
        self.assertEqual(MediaAsset.objects.count(), 0)

    def test_identical_media_is_deduplicated_per_owner_and_download_is_private(self):
        first = self.request(
            "post",
            reverse("mediaasset-list"),
            {"title": "First", "file": self.image()},
            format="multipart",
        )
        owner = user.make()
        self.client.force_authenticate(owner)
        second = self.request(
            "post",
            reverse("mediaasset-list"),
            {"title": "Other", "file": self.image()},
            format="multipart",
        )
        self.assertNotEqual(first.data["id"], second.data["id"])
        self.assertEqual(
            self.request(
                "get", reverse("mediaasset-download", args=[first.data["id"]])
            ).status_code,
            404,
        )
        response = self.request(
            "get", reverse("mediaasset-download", args=[second.data["id"]])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), self.image().read())

    def test_thumbnails_are_assets_even_without_saving_a_cover_and_can_be_reused(self):
        with patch(
            "apps.videomanagement.services.media.covers.generate_cover_image",
            return_value=self.image().read(),
        ):
            first = generate_cover_task.run(
                str(self.video.pk), str(self.user.pk), {"title": "First"}
            )
        with patch(
            "apps.videomanagement.services.media.covers.generate_cover_image",
            return_value=self.image("red").read(),
        ):
            second = generate_cover_task.run(
                str(self.video.pk), str(self.user.pk), {"title": "Second"}
            )
        self.assertNotEqual(first["asset_id"], second["asset_id"])
        self.assertEqual(MediaAsset.objects.count(), 2)
        self.video.refresh_from_db()
        self.assertFalse(self.video.cover)
        for asset in MediaAsset.objects.all():
            self.assertIn("ai thumbnail", asset.tags)
        response = self.request(
            "post",
            reverse("mediaasset-use", args=[first["asset_id"]]),
            {"video_id": str(self.video.pk), "purpose": "cover"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.video.refresh_from_db()
        self.assertTrue(self.video.cover)
        with self.video.cover.open("rb") as cover:
            self.assertEqual(cover.read(), self.image().read())
        self.assertEqual(MediaAsset.objects.count(), 2)

    def test_reference_images_are_saved_and_missing_files_are_skipped(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.video.reference_image.save("reference.png", self.image())
        self.assertEqual(MediaAsset.objects.count(), 1)
        self.assertIn("reference image", MediaAsset.objects.get().tags)
        scene = Scene.objects.create(video=self.video, text="Missing")
        visual = SceneImage.objects.create(scene=scene, file="missing.png")
        self.assertIsNone(visual.asset_id)
        self.assertEqual(MediaAsset.objects.count(), 1)

    def test_asset_job_results_remain_owner_bound_and_handle_deleted_assets(self):
        visual = self.make_visual()
        with patch("apps.videomanagement.tasks.generate_cover_task.apply_async"):
            queued = self.request(
                "post",
                reverse("video-cover-generate", args=[self.video.pk]),
                {},
                format="json",
            )
        endpoint = reverse("video-cover-job", args=[self.video.pk])
        result = Mock(state="SUCCESS", result={"asset_id": str(visual.asset_id)})
        with patch(
            "apps.videomanagement.services.media.cover_jobs.AsyncResult",
            return_value=result,
        ):
            response = self.request(
                "get", endpoint, {"job": queued.data["id"], "image": "1"}
            )
            self.assertEqual(response.content, self.image().read())
            foreign = MediaAsset.objects.create(
                created_by=user.make(),
                kind="IMAGE",
                title="Private",
                file=self.image("green"),
            )
            result.result = {"asset_id": str(foreign.pk)}
            self.assertEqual(
                self.request("get", endpoint, {"job": queued.data["id"]}).data[
                    "status"
                ],
                "FAILED",
            )
            result.result = {"asset_id": str(visual.asset_id)}
            visual.asset.delete()
            self.assertEqual(
                self.request("get", endpoint, {"job": queued.data["id"]}).data[
                    "status"
                ],
                "FAILED",
            )

    def test_video_clips_are_archived_with_their_duration(self):
        path = self.media_root / "source.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=64x64:d=0.25",
                "-pix_fmt",
                "yuv420p",
                str(path),
            ],
            check=True,
            timeout=20,
        )
        scene = Scene.objects.create(video=self.video, text="Clip")
        with self.captureOnCommitCallbacks(execute=True), path.open("rb") as source:
            visual = SceneImage.objects.create(
                scene=scene, file=File(source, name="clip.mp4")
            )
        asset = visual.asset
        self.assertEqual(asset.kind, "VIDEO")
        self.assertIn("scene video", asset.tags)
        self.assertGreater(asset.duration, 0)
        self.assertLess(asset.duration, 1)
        self.assertNotEqual(asset.file.name, visual.file.name)
