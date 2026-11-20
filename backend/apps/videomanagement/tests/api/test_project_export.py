import hashlib
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from django.urls import reverse
from django.test import override_settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from apps.common.r2_storage import _verified
from apps.common.tests.test_r2_storage import MemoryR2
from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import scene
from apps.videomanagement.models import (
    Icon,
    Intro,
    MediaAsset,
    Music,
    Outro,
    SceneImage,
    VideoShare,
)

from .base import ApiTestCase


async def body(response):
    return b"".join([part async for part in response.streaming_content])


@override_settings(R2_STORAGE_ENABLED=False)
class ProjectExportTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        self.video = self.video_for(
            title="Portable story",
            notes="Keep the opening short",
            description="A story",
            settings={
                "subtitles": True,
                "caption_config": {"font": "DejaVu Sans", "api_key": "hidden"},
                "api_key": "secret",
                "export_fps": 30,
            },
            output=ContentFile(b"finished-video", name="output.mp4"),
        )
        self.scene = scene.make(
            video=self.video,
            file=ContentFile(b"narration", name="voice.wav"),
            text="The opening",
            overlays=[],
            audio_settings={"volume": 0.5},
        )
        self.asset = MediaAsset.objects.create(
            created_by=self.user,
            title="Still",
            kind="IMAGE",
            file=ContentFile(b"image-content", name="still.png"),
        )
        SceneImage.objects.create(
            scene=self.scene, asset=self.asset, prompt="A bright day"
        )
        SceneImage.objects.create(
            scene=self.scene, asset=self.asset, prompt="The same visual"
        )
        self.scene.starting_asset = self.asset
        self.scene.save(update_fields=["starting_asset"])
        self.url = reverse("video-export-project", args=[self.video.pk])

    def download(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["X-Accel-Buffering"], "no")
        return ZipFile(io.BytesIO(async_to_sync(body)(response)))

    def test_archive_contains_portable_data_and_deduplicated_verified_media(self):
        VideoShare.objects.create(video=self.video)
        with self.download() as bundle:
            self.assertIsNone(bundle.testzip())
            manifest = json.loads(bundle.read("project.json"))
            self.assertEqual(manifest["format"], "viddie-project")
            self.assertEqual(manifest["version"], 1)
            self.assertEqual(manifest["project"]["title"], "Portable story")
            self.assertEqual(manifest["project"]["notes"], "Keep the opening short")
            self.assertEqual(manifest["project"]["settings"]["export_fps"], 30)
            self.assertIsNone(manifest["project"]["output"])
            self.assertEqual(manifest["scenes"][0]["text"], "The opening")
            self.assertEqual(manifest["scenes"][0]["audio_settings"]["volume"], 0.5)
            visuals = manifest["scenes"][0]["visuals"]
            self.assertEqual(visuals[0]["asset"]["file"], visuals[1]["asset"]["file"])
            self.assertEqual(
                visuals[0]["asset"]["file"],
                manifest["scenes"][0]["starting_asset"]["file"],
            )
            self.assertEqual(len(manifest["files"]), 2)
            for entry in manifest["files"]:
                content = bundle.read(entry["path"])
                self.assertEqual(entry["size"], len(content))
                self.assertEqual(entry["sha256"], hashlib.sha256(content).hexdigest())
                self.assertTrue(entry["path"].startswith("media/"))
            serialized = bundle.read("project.json").decode()
            for private in (
                "secret",
                "api_key",
                "created_by",
                str(self.user.pk),
                "public_share",
                str(self.video.public_share.token),
                self.asset.file.name,
            ):
                self.assertNotIn(private, serialized)

    def test_finished_video_is_opt_in_and_archived_scenes_are_excluded(self):
        scene.make(
            video=self.video,
            text="Removed",
            archived_at=timezone.now(),
            file="missing.wav",
        )
        with self.download(include_output="true") as bundle:
            manifest = json.loads(bundle.read("project.json"))
            self.assertEqual(
                bundle.read(manifest["project"]["output"]), b"finished-video"
            )
            self.assertEqual(len(manifest["scenes"]), 1)

    def test_preflight_returns_download_url_without_reading_media_bodies(self):
        with patch(
            "apps.videomanagement.services.videos.project_export.source_chunks"
        ) as read:
            response = self.client.get(
                self.url, {"check_only": "true", "include_output": "true"}
            )
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        self.assertTrue(
            response.json()["download_url"].endswith("?include_output=true")
        )
        self.assertEqual(response.json()["filename"], "portable-story-project.zip")
        read.assert_not_called()

    def test_native_download_authenticates_using_the_access_cookie(self):
        self.client.force_authenticate(None)
        self.client.cookies["access_token"] = str(AccessToken.for_user(self.user))
        with self.download() as bundle:
            self.assertIsNone(bundle.testzip())

    def test_music_intros_overlays_and_diagram_icons_are_included(self):
        self.video.music = Music.objects.create(
            created_by=self.user,
            name="Song",
            file=ContentFile(b"music", name="song.mp3"),
        )
        self.video.intro = Intro.objects.create(
            created_by=self.user,
            name="Opening",
            file=ContentFile(b"intro", name="intro.mp4"),
        )
        self.video.outro = Outro.objects.create(
            created_by=self.user,
            name="Ending",
            file=ContentFile(b"outro", name="outro.mp4"),
        )
        self.video.cover = self.asset.file.name
        self.video.save(update_fields=["music", "intro", "outro", "cover"])
        self.scene.voiceover.save("recording.wav", ContentFile(b"recording"))
        self.scene.overlay_logo.save("logo.png", ContentFile(b"logo"))
        Icon.objects.create(
            key="custom:one",
            created_by=self.user,
            collection="custom",
            name="One",
            file=ContentFile(b"<svg/>", name="one.svg"),
            license="CC0",
            attribution="Creator",
        )
        self.scene.overlays = [
            {
                "kind": "diagram",
                "diagram": {
                    "template": "comparison",
                    "items": [{"icon": "custom:one", "label": "One"}, {"label": "Two"}],
                },
            }
        ]
        self.scene.audio_settings = {"duration": 5, "volume": 0.5}
        self.scene.save(update_fields=["overlays", "audio_settings"])
        with self.download() as bundle:
            manifest = json.loads(bundle.read("project.json"))
            for name, content in (
                ("music", b"music"),
                ("intro", b"intro"),
                ("outro", b"outro"),
            ):
                self.assertEqual(
                    bundle.read(manifest["project"][name]["file"]), content
                )
            self.assertEqual(
                bundle.read(manifest["scenes"][0]["voiceover"]), b"recording"
            )
            self.assertEqual(
                bundle.read(manifest["scenes"][0]["overlay_logo"]), b"logo"
            )
            self.assertEqual(manifest["scenes"][0]["audio_settings"]["duration"], 5)
            self.assertEqual(bundle.read(manifest["icons"][0]["file"]), b"<svg/>")
            self.assertEqual(manifest["icons"][0]["attribution"], "Creator")
            self.assertIsNone(bundle.testzip())

    def test_permission_checks_apply_to_preflight_and_download(self):
        self.client.force_authenticate(user.make())
        for params in ({}, {"check_only": "true"}):
            self.assertEqual(self.client.get(self.url, params).status_code, 404)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(self.url).status_code, (401, 403))

    def test_missing_media_invalid_options_and_processing_fail_before_streaming(self):
        self.assertEqual(
            self.client.get(self.url, {"include_output": "invalid"}).status_code, 400
        )
        self.video.status = "RENDERING"
        self.video.save(update_fields=["status"])
        self.assertEqual(self.client.get(self.url).status_code, 400)
        self.video.status = "READY"
        self.video.save(update_fields=["status"])
        self.asset.file.storage.delete(self.asset.file.name)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("missing", str(response.data))

    @override_settings(
        R2_STORAGE_ENABLED=True,
        R2_ACCOUNT_ID="a" * 32,
        R2_BUCKET_NAME="test-bucket",
        R2_ACCESS_KEY_ID="test",
        R2_SECRET_ACCESS_KEY="test",
        R2_JURISDICTION="",
    )
    def test_r2_export_streams_remote_bytes_without_materializing_local_cache(self):
        archive = MemoryR2()
        _verified.clear()
        with patch("apps.common.r2_storage._archive", return_value=archive):
            for field in (self.video.output, self.scene.file, self.asset.file):
                field.storage.sync(field.name)
                Path(field.storage.location, field.name).unlink()
            with patch(
                "apps.common.r2_storage.R2StorageMixin.path",
                side_effect=AssertionError("No cache reads"),
            ):
                with self.download(include_output="true") as bundle:
                    manifest = json.loads(bundle.read("project.json"))
                    self.assertEqual(
                        bundle.read(manifest["project"]["output"]), b"finished-video"
                    )
                    self.assertIsNone(bundle.testzip())
            self.assertEqual(len(archive.requests), 3)
            self.assertTrue(all("IfMatch" in request for request in archive.requests))

    def test_changed_source_fails_verification_instead_of_completing_a_zip(self):
        response = self.client.get(self.url)
        Path(self.asset.file.path).write_bytes(b"changed")
        with self.assertRaises(OSError):
            async_to_sync(body)(response)
