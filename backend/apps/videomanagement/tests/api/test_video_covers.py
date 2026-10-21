from io import BytesIO
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import Mock, patch

from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from .base import ApiTestCase
from apps.usermanagement.baker_recipes import user


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

    def uploaded_image(self):
        image = BytesIO()
        Image.new("RGB", (640, 360), "red").save(image, format="PNG")
        return SimpleUploadedFile(
            "cover.png", image.getvalue(), content_type="image/png"
        )

    def test_uploaded_and_ai_images_save_the_preview_without_generation(self):
        empty = self.video_for(status="READY")
        for source in ("upload", "ai"):
            with (
                self.subTest(source=source),
                patch(
                    "apps.videomanagement.services.media.covers.generate_cover_image"
                ) as generate,
            ):
                values = {
                    "source": source,
                    "title": "Custom cover",
                    "background": False,
                }
                preview = self.client.post(
                    reverse("video-cover-preview", args=[empty.pk]),
                    {**values, "image": self.uploaded_image()},
                    format="multipart",
                )
                self.assertEqual(preview.status_code, 200)
                saved = self.client.post(
                    reverse("video-cover", args=[empty.pk]),
                    {**values, "image": self.uploaded_image()},
                    format="multipart",
                )
                self.assertEqual(saved.status_code, 200, saved.data)
                self.assertNotIn("image", saved.data["cover_settings"])
                self.assertEqual(saved.data["cover_settings"]["source"], source)
                download = self.client.get(
                    reverse("video-cover-download", args=[empty.pk])
                )
                self.assertEqual(b"".join(download.streaming_content), preview.content)
                generate.assert_not_called()
        empty.refresh_from_db()
        self.assertEqual(empty.status, "READY")
        self.assertFalse(empty.output)

    def test_generate_returns_draft_and_checks_ownership_before_provider(self):
        endpoint = reverse("video-cover-generate", args=[self.video.pk])
        with patch(
            "apps.videomanagement.views.covers.queue_cover",
            return_value={"id": "signed-job", "status": "QUEUED"},
        ) as generate:
            response = self.client.post(
                endpoint,
                {"prompt": "Dramatic lighting", "title": "A title in the artwork"},
                format="json",
            )
            self.assertEqual(response.status_code, 202)
            self.assertEqual(response.data["id"], "signed-job")
            self.assertEqual(
                generate.call_args.args[2]["title"], "A title in the artwork"
            )
            self.assertEqual(generate.call_args.args[1], self.user)
            self.assertEqual(generate.call_args.args[2]["prompt"], "Dramatic lighting")
            self.video.refresh_from_db()
            self.assertFalse(self.video.cover)
            other = self.video_for(owner=user.make())
            generate.reset_mock()
            self.assertEqual(
                self.client.post(
                    reverse("video-cover-generate", args=[other.pk]), {}, format="json"
                ).status_code,
                404,
            )
            self.assertEqual(
                self.client.post(
                    endpoint, {"prompt": "x" * 1501}, format="json"
                ).status_code,
                400,
            )
            generate.assert_not_called()

    def test_image_sources_require_valid_image(self):
        endpoint = reverse("video-cover", args=[self.video.pk])
        for source in ("ai", "upload"):
            self.assertEqual(
                self.client.post(
                    endpoint, {"source": source}, format="json"
                ).status_code,
                400,
            )
            invalid = SimpleUploadedFile(
                "cover.png", b"not an image", content_type="image/png"
            )
            self.assertEqual(
                self.client.post(
                    endpoint, {"source": source, "image": invalid}, format="multipart"
                ).status_code,
                400,
            )

    def test_generation_failure_preserves_saved_cover(self):
        saved = self.client.post(
            reverse("video-cover", args=[self.video.pk]), {}, format="json"
        )
        self.assertEqual(saved.status_code, 200)
        self.video.refresh_from_db()
        previous = self.video.cover.name
        with patch(
            "apps.videomanagement.tasks.generate_cover_task.apply_async",
            side_effect=ConnectionError("Queue unavailable"),
        ):
            response = self.client.post(
                reverse("video-cover-generate", args=[self.video.pk]), {}, format="json"
            )
        self.assertEqual(response.status_code, 503)
        self.video.refresh_from_db()
        self.assertEqual(self.video.cover.name, previous)
        self.assertTrue(self.video.cover.storage.exists(previous))

    def test_ai_can_generate_before_export(self):
        from apps.videomanagement.services.media.covers import generate_cover_image

        empty = self.video_for(status="READY")
        generated = self.root / "draft.png"
        Image.new("RGB", (600, 400), "green").save(generated)
        with patch(
            "apps.videomanagement.integrations.visuals.openai_images.generate_openai_image",
            return_value=generated,
        ) as generate:
            result = generate_cover_image(
                empty, self.user, {"prompt": "Warm light", "time": 0}
            )
        self.assertIsNone(generate.call_args.kwargs["reference"])
        self.assertEqual(Image.open(BytesIO(result)).size, (1280, 720))

    def test_ai_uses_real_reference_and_returns_youtube_size(self):
        from apps.videomanagement.services.media.covers import generate_cover_image

        generated = self.root / "generated.png"
        Image.new("RGB", (600, 400), "green").save(generated)

        def generate(*args, **kwargs):
            self.assertTrue(Path(kwargs["reference"]).exists())
            self.assertEqual(kwargs["user"], self.user)
            self.assertIn(self.video.title, args[0])
            self.assertIn("MY EXACT TITLE", args[0])
            self.assertNotIn("Do not draw text", args[0])
            return generated

        with patch(
            "apps.videomanagement.integrations.visuals.openai_images.generate_openai_image",
            side_effect=generate,
        ):
            result = generate_cover_image(
                self.video,
                self.user,
                {"prompt": "Warm light", "time": 0.25, "title": "MY EXACT TITLE"},
            )
        self.assertEqual(Image.open(BytesIO(result)).size, (1280, 720))

    def test_background_job_status_image_and_signed_ownership(self):
        import base64

        with patch(
            "apps.videomanagement.tasks.generate_cover_task.apply_async"
        ) as dispatch:
            response = self.client.post(
                reverse("video-cover-generate", args=[self.video.pk]),
                {"title": "Exact title"},
                format="json",
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(dispatch.call_args.kwargs["args"][2]["title"], "Exact title")
        job = response.data["id"]
        endpoint = reverse("video-cover-job", args=[self.video.pk])
        with patch(
            "apps.videomanagement.services.media.cover_jobs.AsyncResult",
            return_value=Mock(state="STARTED"),
        ):
            self.assertEqual(
                self.client.get(endpoint, {"job": job}).data["status"], "RUNNING"
            )
        result = Mock(
            state="SUCCESS", result={"image": base64.b64encode(b"image draft").decode()}
        )
        with patch(
            "apps.videomanagement.services.media.cover_jobs.AsyncResult",
            return_value=result,
        ) as load:
            self.assertEqual(
                self.client.get(endpoint, {"job": job}).data, {"status": "SUCCEEDED"}
            )
            self.assertEqual(
                self.client.get(endpoint, {"job": job, "image": "1"}).content,
                b"image draft",
            )
            other = self.video_for()
            self.assertEqual(
                self.client.get(
                    reverse("video-cover-job", args=[other.pk]), {"job": job}
                ).status_code,
                404,
            )
            self.assertEqual(
                self.client.get(endpoint, {"job": "tampered"}).status_code, 404
            )
            self.assertEqual(load.call_count, 2)
        with patch(
            "apps.videomanagement.services.media.cover_jobs.AsyncResult",
            return_value=Mock(state="FAILURE"),
        ):
            self.assertEqual(
                self.client.get(endpoint, {"job": job}).data["status"], "FAILED"
            )
        self.video.refresh_from_db()
        self.assertFalse(self.video.cover)
        self.assertEqual(self.video.status, "COMPLETED")

    def test_background_worker_uses_owner_and_returns_draft(self):
        import base64
        from apps.videomanagement.tasks import generate_cover_task

        with patch(
            "apps.videomanagement.services.media.covers.generate_cover_image",
            return_value=b"draft",
        ) as generate:
            result = generate_cover_task.run(
                str(self.video.pk), str(self.user.pk), {"title": "Draw this"}
            )
        self.assertEqual(base64.b64decode(result["image"]), b"draft")
        self.assertEqual(generate.call_args.args[1], self.user)
        self.assertEqual(generate.call_args.args[2]["title"], "Draw this")
        self.video.refresh_from_db()
        self.assertFalse(self.video.cover)

    def test_ai_title_is_not_overlaid_again(self):
        from apps.videomanagement.serializers.covers import CoverSerializer
        from apps.videomanagement.services.media.covers import create_cover

        serializer = CoverSerializer(
            data={
                "source": "ai",
                "image": self.uploaded_image(),
                "title": "Already in artwork",
            }
        )
        serializer.is_valid(raise_exception=True)
        with patch("apps.videomanagement.services.media.covers.cover_font") as font:
            result = create_cover(self.video, serializer.validated_data)
        font.assert_not_called()
        self.assertEqual(Image.open(BytesIO(result)).getpixel((320, 180)), (255, 0, 0))

    def test_reference_prefers_identity_then_scene_art_over_export(self):
        from apps.videomanagement.models import Scene, SceneImage
        from apps.videomanagement.services.media.covers import cover_reference

        scene = Scene.objects.create(video=self.video, text="The actual scene")
        SceneImage.objects.create(scene=scene, file="missing.png")
        visual = SceneImage.objects.create(scene=scene, file=self.uploaded_image())
        with patch("apps.videomanagement.services.media.covers.frame_image") as frame:
            self.assertEqual(
                cover_reference(self.video, str(self.root)), visual.file.path
            )
            self.video.reference_image.save("identity.png", self.uploaded_image())
            self.assertEqual(
                cover_reference(self.video, str(self.root)),
                self.video.reference_image.path,
            )
            frame.assert_not_called()

    def test_export_reference_skips_intro_and_outro(self):
        from apps.videomanagement.models import Intro, Outro
        from apps.videomanagement.services.media.covers import cover_reference

        self.video.intro = Intro.objects.create(
            name="Intro", file=self.video.output.name
        )
        self.video.outro = Outro.objects.create(
            name="Outro", file=self.video.output.name
        )
        with (
            patch(
                "apps.videomanagement.services.media.covers.media_timing",
                side_effect=[{"duration": 100}, {"duration": 10}, {"duration": 20}],
            ),
            patch(
                "apps.videomanagement.services.media.covers.frame_image",
                return_value=Image.new("RGB", (320, 180)),
            ) as frame,
        ):
            reference = cover_reference(self.video, str(self.root))
        frame.assert_called_once_with(self.video, 45)
        self.assertTrue(Path(reference).exists())
