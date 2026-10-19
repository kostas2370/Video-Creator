import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from django.core.files import File
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.usermanagement.baker_recipes import user

from .base import ApiTestCase


class VideoCoverTests(ApiTestCase):
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
                "color=c=blue:s=320x180:d=1",
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

    def test_real_frame_preview_save_download_and_library_cover(self):
        values = {
            "time": 0.25,
            "title": "My cover",
            "font": "Poppins",
            "position": "middle",
        }
        preview = self.client.post(
            reverse("video-cover-preview", args=[self.video.pk]), values, format="json"
        )
        self.assertEqual(preview.status_code, 200)
        image = Image.open(BytesIO(preview.content))
        self.assertEqual(image.size, (320, 180))
        self.assertGreater(len(image.getcolors(320 * 180)), 1)
        self.video.refresh_from_db()
        self.assertFalse(self.video.cover)
        saved = self.client.post(
            reverse("video-cover", args=[self.video.pk]), values, format="json"
        )
        self.assertEqual(saved.status_code, 200, saved.data)
        self.video.refresh_from_db()
        self.assertTrue(self.video.cover.storage.exists(self.video.cover.name))
        self.assertEqual(self.video.cover_settings["font"], "Poppins")
        self.assertEqual(self.video.status, "COMPLETED")
        download = self.client.get(
            reverse("video-cover-download", args=[self.video.pk])
        )
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b"".join(download.streaming_content), preview.content)
        self.assertTrue(
            self.client.get(reverse("video-list")).data["results"][0]["cover"]
        )

    def test_frames_fonts_and_foreign_video_are_validated(self):
        endpoint = reverse("video-cover-preview", args=[self.video.pk])
        for values in (
            {"time": 5},
            {"time": -1},
            {"font": "/tmp/font.ttf"},
            {"color": "red"},
            {"title": "x" * 101},
        ):
            self.assertEqual(
                self.client.post(endpoint, values, format="json").status_code, 400
            )
        other = self.video_for(owner=user.make())
        self.assertEqual(
            self.client.post(
                reverse("video-cover", args=[other.pk]), {}, format="json"
            ).status_code,
            404,
        )
        self.video.status = "RENDERING"
        self.video.save()
        self.assertEqual(self.client.post(endpoint, {}, format="json").status_code, 400)

    def test_cover_requires_an_export_and_all_fonts_load(self):
        empty = self.video_for(status="READY")
        self.assertEqual(
            self.client.post(
                reverse("video-cover-preview", args=[empty.pk]), {}, format="json"
            ).status_code,
            400,
        )
        for font in (
            "DejaVu Sans",
            "DejaVu Serif",
            "DejaVu Sans Mono",
            "Poppins",
            "Lato",
            "Bebas Neue",
        ):
            response = self.client.post(
                reverse("video-cover-preview", args=[self.video.pk]),
                {"title": "Cover", "font": font},
                format="json",
            )
            self.assertEqual(
                response.status_code, 200, (font, getattr(response, "data", None))
            )
