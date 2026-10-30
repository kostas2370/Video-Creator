import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.core.files import File
from django.core.files.base import ContentFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import scene, scene_image
from ...models import Video
from ...services.media.thumbnails import thumbnail_time
from .base import ApiTestCase

SERVICE = "apps.videomanagement.services.media.thumbnails"


class VideoThumbnailTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        override = override_settings(MEDIA_ROOT=self.root)
        override.enable()
        self.addCleanup(override.disable)
        self.source = self.root / "source.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=800x450:d=1",
                "-pix_fmt",
                "yuv420p",
                str(self.source),
            ],
            check=True,
            timeout=20,
        )
        self.video = self.video_for(status="COMPLETED")
        with self.source.open("rb") as file:
            self.video.output.save("export.mp4", File(file))
        self.url = reverse("video-thumbnail", args=[self.video.pk])

    def test_saves_one_real_jpeg_and_reuses_it_without_decoding_again(self):
        original_time = self.video.updated_at
        with patch(SERVICE + ".random.uniform", return_value=0.5) as sample:
            first = self.client.post(self.url, {}, format="json")
            second = self.client.post(self.url, {}, format="json")
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(second.data, first.data)
        sample.assert_called_once()
        self.video.refresh_from_db()
        self.assertTrue(self.video.thumbnail)
        self.assertEqual(self.video.status, "COMPLETED")
        self.assertEqual(self.video.updated_at, original_time)
        image = Image.open(self.video.thumbnail.path)
        self.assertEqual(image.format, "JPEG")
        self.assertLessEqual(max(image.size), 640)
        self.assertGreater(
            image.getpixel((image.width // 2, image.height // 2))[2], 200
        )
        listed = self.client.get(reverse("video-list"))
        self.assertTrue(
            listed.data["results"][0]["thumbnail"].endswith(self.video.thumbnail.name)
        )
        self.assertEqual(len(list(self.root.glob("media/thumbnails/**/*.jpg"))), 1)

    def test_saved_cover_takes_priority_and_missing_thumbnail_files_are_repaired(self):
        output = BytesIO()
        Image.new("RGB", (32, 32), "red").save(output, format="PNG")
        self.video.cover.save("cover.png", ContentFile(output.getvalue()))
        with patch(SERVICE + ".random.uniform") as sample:
            response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["thumbnail"].endswith(self.video.cover.name))
        sample.assert_not_called()
        self.video.cover = ""
        self.video.thumbnail = "media/thumbnails/missing.jpg"
        self.video.save(update_fields=["cover", "thumbnail"])
        self.assertEqual(self.client.post(self.url, {}, format="json").status_code, 200)
        self.video.refresh_from_db()
        self.assertTrue(Path(self.video.thumbnail.path).exists())

    def test_draft_clip_can_generate_a_saved_thumbnail(self):
        self.video.output = ""
        self.video.status = "READY"
        self.video.save(update_fields=["output", "status"])
        visual = scene_image.make(scene=scene.make(video=self.video), file="")
        with self.source.open("rb") as file:
            visual.file = File(file, name="gameplay.mp4")
            visual.save()
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.video.refresh_from_db()
        self.assertTrue(self.video.thumbnail)
        self.assertEqual(self.video.status, "READY")

    def test_rendering_missing_media_and_foreign_projects_do_not_generate(self):
        self.video.status = "RENDERING"
        self.video.save(update_fields=["status"])
        foreign = self.video_for(owner=user.make())
        with patch(SERVICE + ".random.uniform") as sample:
            self.assertEqual(
                self.client.post(self.url, {}, format="json").status_code, 400
            )
            self.assertEqual(
                self.client.post(
                    reverse("video-thumbnail", args=[foreign.pk]), {}, format="json"
                ).status_code,
                404,
            )
            self.video.status = "READY"
            self.video.output = ""
            self.video.save(update_fields=["output", "status"])
            self.assertEqual(
                self.client.post(self.url, {}, format="json").status_code, 400
            )
            self.client.force_authenticate(None)
            self.assertIn(
                self.client.post(self.url, {}, format="json").status_code, (401, 403)
            )
        sample.assert_not_called()

    def test_encoder_failure_keeps_the_export_and_does_not_save_an_image(self):
        with (
            patch(SERVICE + ".media_timing", return_value={"duration": 1}),
            patch(
                SERVICE + ".extract_video_frame",
                side_effect=subprocess.TimeoutExpired("ffmpeg", 20),
            ),
        ):
            response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.video.refresh_from_db()
        self.assertFalse(self.video.thumbnail)
        self.assertEqual(self.video.status, "COMPLETED")
        self.assertTrue(Path(self.video.output.path).exists())

    def test_frame_selection_stays_inside_content_after_intro_before_outro(self):
        with patch(SERVICE + ".random.uniform", return_value=0.35):
            self.assertAlmostEqual(thumbnail_time(100, intro=20, outro=10), 44.5)
        with patch(SERVICE + ".random.uniform", return_value=0.75):
            self.assertAlmostEqual(thumbnail_time(100, intro=20, outro=10), 72.5)

    def test_new_render_during_extraction_does_not_save_a_stale_thumbnail(self):
        image = BytesIO()
        Image.new("RGB", (32, 32), "blue").save(image, format="JPEG")

        def start_render(*args, **kwargs):
            Video.objects.filter(pk=self.video.pk).update(status="RENDERING")
            return image.getvalue()

        with (
            patch(SERVICE + ".media_timing", return_value={"duration": 1}),
            patch(SERVICE + ".extract_video_frame", side_effect=start_render),
        ):
            response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.video.refresh_from_db()
        self.assertFalse(self.video.thumbnail)
        self.assertFalse(list(self.root.glob("media/thumbnails/**/*.jpg")))

    def test_another_workers_thumbnail_wins_without_leaving_a_duplicate_file(self):
        image = BytesIO()
        Image.new("RGB", (32, 32), "blue").save(image, format="JPEG")
        existing = self.root / "media/thumbnails/other.jpg"
        existing.parent.mkdir(parents=True)
        existing.write_bytes(image.getvalue())

        def save_elsewhere(*args, **kwargs):
            Video.objects.filter(pk=self.video.pk).update(
                thumbnail="media/thumbnails/other.jpg"
            )
            return image.getvalue()

        with (
            patch(SERVICE + ".media_timing", return_value={"duration": 1}),
            patch(SERVICE + ".extract_video_frame", side_effect=save_elsewhere),
        ):
            response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["thumbnail"].endswith("/other.jpg"))
        self.assertEqual(list(self.root.glob("media/thumbnails/**/*.jpg")), [existing])
