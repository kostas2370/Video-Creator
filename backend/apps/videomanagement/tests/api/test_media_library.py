from io import BytesIO
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch
import wave

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from .base import ApiTestCase
from ...models import MediaAsset
from ...baker_recipes import scene
from apps.usermanagement.baker_recipes import user


class MediaLibraryTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        override = override_settings(MEDIA_ROOT=self.directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.url = reverse("mediaasset-list")

    def image(self, name="photo.png"):
        data = BytesIO()
        Image.new("RGB", (64, 64), "blue").save(data, "PNG")
        return SimpleUploadedFile(name, data.getvalue(), content_type="image/png")

    def upload(self):
        response = self.client.post(
            self.url,
            {
                "title": "Greek coast",
                "file": self.image(),
                "tags": '["Travel", "summer"]',
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return MediaAsset.objects.get(pk=response.data["id"])

    def test_upload_tag_search_type_filter_and_ownership(self):
        asset = self.upload()
        self.assertEqual(asset.tags, ["travel", "summer"])
        self.assertEqual(asset.kind, "IMAGE")
        self.assertEqual(
            self.client.get(self.url, {"search": "travel"}).data["count"], 1
        )
        self.assertEqual(
            self.client.get(self.url, {"search": "coast"}).data["count"], 1
        )
        self.assertEqual(self.client.get(self.url, {"kind": "AUDIO"}).data["count"], 0)
        self.assertEqual(self.client.get(self.url, {"kind": "VISUAL"}).data["count"], 1)
        foreign = MediaAsset.objects.create(
            created_by=user.make(), title="Private", file=self.image(), kind="IMAGE"
        )
        self.assertEqual(self.client.get(self.url).data["count"], 1)
        self.assertEqual(
            self.client.get(
                reverse("mediaasset-detail", args=[foreign.pk])
            ).status_code,
            404,
        )
        change = self.client.patch(
            reverse("mediaasset-detail", args=[asset.pk]),
            {"tags": ["favorites"], "title": "Favorite"},
            format="json",
        )
        self.assertEqual(change.status_code, 200, change.data)
        self.assertEqual(change.data["tags"], ["favorites"])

    def test_reuse_copies_files_and_library_removal_does_not_break_scenes(self):
        asset = self.upload()
        video = self.video_for(status="READY", video_type="MANUAL")
        response = self.client.post(
            reverse("mediaasset-use", args=[asset.pk]),
            {"video_id": str(video.pk), "purpose": "new_scene", "duration": 3},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        item = video.scenes.get()
        visual = item.scene_images.get()
        self.assertNotEqual(visual.file.name, asset.file.name)
        self.assertEqual(item.audio_settings["duration"], 3)
        with self.captureOnCommitCallbacks(execute=True):
            deleted = self.client.delete(reverse("mediaasset-detail", args=[asset.pk]))
        self.assertEqual(deleted.status_code, 204)
        self.assertTrue(visual.file.storage.exists(visual.file.name))

    def test_replace_visual_rejects_foreign_projects_and_processing(self):
        asset = self.upload()
        video = self.video_for(status="READY")
        item = scene.make(video=video)
        url = reverse("mediaasset-use", args=[asset.pk])
        response = self.client.post(
            url,
            {"video_id": str(video.pk), "scene_id": str(item.pk), "purpose": "visual"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(item.scene_images.exists())
        other = self.video_for(owner=user.make(), status="READY")
        self.assertEqual(
            self.client.post(
                url, {"video_id": str(other.pk), "purpose": "new_scene"}, format="json"
            ).status_code,
            404,
        )
        video.status = "RENDERING"
        video.save()
        self.assertEqual(
            self.client.post(
                url, {"video_id": str(video.pk), "purpose": "new_scene"}, format="json"
            ).status_code,
            409,
        )

    def test_audio_upload_and_music_reuse(self):
        data = BytesIO()
        with wave.open(data, "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(8000)
            stream.writeframes(b"\0\0" * 8000)
        response = self.client.post(
            self.url,
            {
                "title": "Track",
                "file": SimpleUploadedFile(
                    "track.wav", data.getvalue(), content_type="audio/wav"
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["kind"], "AUDIO")
        video = self.video_for(status="READY")
        result = self.client.post(
            reverse("mediaasset-use", args=[response.data["id"]]),
            {"video_id": str(video.pk), "purpose": "music"},
            format="json",
        )
        self.assertEqual(result.status_code, 200, result.data)
        video.refresh_from_db()
        self.assertTrue(video.music.file)

    def test_rejects_invalid_media_tags_and_file_replacement(self):
        bad = self.client.post(
            self.url,
            {"title": "Bad", "file": SimpleUploadedFile("fake.png", b"not an image")},
            format="multipart",
        )
        self.assertEqual(bad.status_code, 400)
        asset = self.upload()
        detail = reverse("mediaasset-detail", args=[asset.pk])
        self.assertEqual(
            self.client.patch(detail, {"tags": "bad"}, format="json").status_code, 400
        )
        self.assertEqual(
            self.client.patch(detail, {"tags": ["x" * 31]}, format="json").status_code,
            400,
        )
        self.assertEqual(
            self.client.patch(
                detail, {"file": self.image()}, format="multipart"
            ).status_code,
            400,
        )

    def test_tags_keep_strict_types_limits_and_normalization(self):
        asset = self.upload()
        detail = reverse("mediaasset-detail", args=[asset.pk])
        invalid = (
            None,
            {},
            "travel",
            [1],
            [True],
            [None],
            [""],
            ["  "],
            ["x" * 31],
            ["tag"] * 13,
            ["İ" * 30],
        )
        for tags in invalid:
            with self.subTest(tags=tags):
                response = self.client.patch(detail, {"tags": tags}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn("tags", response.data)
        response = self.client.patch(
            detail, {"tags": [" Travel ", "TRAVEL", "summer"]}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["tags"], ["travel", "summer"])
        response = self.client.patch(detail, {"tags": []}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["tags"], [])

    def test_video_is_probed_once_and_saved_without_consuming_upload(self):
        path = Path(self.directory.name) / "source.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=64x64:d=1",
                "-pix_fmt",
                "yuv420p",
                str(path),
            ],
            check=True,
            timeout=20,
        )
        content = path.read_bytes()
        with patch(
            "apps.videomanagement.utils.timing.subprocess.run", wraps=subprocess.run
        ) as probe:
            response = self.client.post(
                self.url,
                {
                    "title": "Clip",
                    "file": SimpleUploadedFile("clip.mp4", content),
                },
                format="multipart",
            )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["kind"], MediaAsset.Kind.VIDEO)
        self.assertAlmostEqual(response.data["duration"], 1, places=1)
        probe.assert_called_once()
        asset = MediaAsset.objects.get(pk=response.data["id"])
        with asset.file.open("rb") as stored:
            self.assertEqual(stored.read(), content)

    def test_invalid_video_and_audio_errors_belong_to_file(self):
        for name in ("broken.mp4", "broken.wav", "unsupported.txt"):
            with self.subTest(name=name):
                response = self.client.post(
                    self.url,
                    {
                        "title": "Broken",
                        "file": SimpleUploadedFile(name, b"invalid"),
                    },
                    format="multipart",
                )
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn("file", response.data)

    def test_library_image_pixel_limit(self):
        data = BytesIO()
        Image.new("RGB", (4001, 4000)).save(data, "PNG")
        response = self.client.post(
            self.url,
            {
                "title": "Too large",
                "file": SimpleUploadedFile("large.png", data.getvalue()),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("file", response.data)
