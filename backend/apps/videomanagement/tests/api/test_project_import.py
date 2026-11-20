import hashlib
import io
import json
import subprocess
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.common.r2_storage import _verified
from apps.common.tests.test_r2_storage import MemoryR2
from apps.usermanagement.baker_recipes import user
from apps.videomanagement.models import (
    Icon,
    Intro,
    MediaAsset,
    Music,
    MusicCatalogTrack,
    Outro,
    Scene,
    SceneImage,
    Video,
    VideoShare,
)
from apps.videomanagement.services.captions.alignment import narration_identity
from apps.videomanagement.services.videos.preview import preview_timeline
from apps.videomanagement.utils.cuts import video_cut_source

from .base import ApiTestCase


async def response_bytes(response):
    return b"".join([chunk async for chunk in response.streaming_content])


@override_settings(R2_STORAGE_ENABLED=False)
class ProjectImportTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.directory = directory.name
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        self.video = self.video_for(
            title="Portable story",
            settings={"narration": True, "subtitles": True, "export_fps": 30},
        )
        image = io.BytesIO()
        Image.new("RGB", (16, 16), "blue").save(image, "PNG")
        self.asset = MediaAsset.objects.create(
            created_by=self.user,
            title="Still",
            kind="IMAGE",
            tags=[],
            file=ContentFile(image.getvalue(), name="image.png"),
        )
        audio = io.BytesIO()
        with wave.open(audio, "wb") as source:
            source.setnchannels(1)
            source.setsampwidth(2)
            source.setframerate(8000)
            source.writeframes(b"\0\0" * 8000)
        self.scene = Scene.objects.create(
            video=self.video,
            text="Hello",
            audio_settings={},
            file=ContentFile(audio.getvalue(), name="voice.wav"),
            starting_asset=self.asset,
        )
        SceneImage.objects.create(scene=self.scene, asset=self.asset, prompt="Blue")
        self.scene.caption_alignment = {
            "source": narration_identity(self.scene),
            "words": [{"text": "Hello", "start": 0, "end": 0.5}],
        }
        self.scene.save()
        source = video_cut_source(preview_timeline(self.video).segments)
        self.video.cuts = {
            "source_key": source["key"],
            "source_duration": source["duration"],
            "sections": [{"start": 0, "end": 0.5}],
        }
        self.video.save()
        VideoShare.objects.create(video=self.video)
        self.url = reverse("video-import-project")

    def exported(self, include_output=False):
        response = self.client.get(
            reverse("video-export-project", args=[self.video.pk]),
            {"include_output": include_output},
        )
        self.assertEqual(response.status_code, 200)
        return async_to_sync(response_bytes)(response)

    def edited_archive(self, edit):
        with ZipFile(io.BytesIO(self.exported())) as bundle:
            entries = {name: bundle.read(name) for name in bundle.namelist()}
        manifest = json.loads(entries.pop("project.json"))
        edit(manifest, entries)
        output = io.BytesIO()
        with ZipFile(output, "w", ZIP_STORED) as bundle:
            for name, data in entries.items():
                bundle.writestr(name, data)
            bundle.writestr("project.json", json.dumps(manifest))
        return output.getvalue()

    def upload(self, data):
        return self.client.post(
            self.url,
            {"file": SimpleUploadedFile("project.zip", data, "application/zip")},
            format="multipart",
        )

    def test_round_trip_creates_private_copy_with_media_and_remapped_timing(self):
        old_scene_id = self.scene.pk
        response = self.upload(self.exported())
        self.assertEqual(response.status_code, 201, getattr(response, "data", None))
        video = Video.objects.get(pk=response.data["id"])
        scene = video.scenes.get()
        self.assertNotEqual(video.pk, self.video.pk)
        self.assertNotEqual(scene.pk, old_scene_id)
        self.assertEqual(video.created_by, self.user)
        self.assertEqual(video.status, "READY")
        self.assertIsNone(video.voice_model_id)
        self.assertFalse(VideoShare.objects.filter(video=video).exists())
        self.assertEqual(video.settings["export_fps"], 30)
        self.assertEqual(scene.caption_alignment["source"], narration_identity(scene))
        self.assertEqual(scene.caption_alignment["words"][0]["text"], "Hello")
        self.assertEqual(
            video.cuts["source_key"],
            video_cut_source(preview_timeline(video).segments)["key"],
        )
        self.assertEqual(scene.starting_asset_id, scene.scene_images.get().asset_id)
        self.assertNotEqual(scene.file.name, self.scene.file.name)
        with scene.file.open("rb") as copied, self.scene.file.open("rb") as original:
            self.assertEqual(copied.read(), original.read())
        self.assertTrue(self.asset.file.storage.exists(self.asset.file.name))

    def test_import_can_belong_to_another_user_without_access_to_original(self):
        data = self.exported()
        owner = user.make()
        self.client.force_authenticate(owner)
        response = self.upload(data)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Video.objects.get(pk=response.data["id"]).created_by, owner)
        self.assertEqual(
            self.client.get(reverse("video-detail", args=[self.video.pk])).status_code,
            404,
        )

    def test_invalid_hash_missing_media_and_unsafe_path_make_no_writes(self):
        for edit in (
            lambda manifest, files: manifest["files"][0].update(sha256="0" * 64),
            lambda manifest, files: files.pop(next(iter(files))),
            lambda manifest, files: files.update({"../escape.png": b"unsafe"}),
            lambda manifest, files: manifest.update(version=2),
            lambda manifest, files: manifest["scenes"].append(manifest["scenes"][0]),
            lambda manifest, files: manifest["project"].update(
                source_audio="/etc/passwd"
            ),
            lambda manifest, files: manifest["scenes"][0].update(
                cuts={"source_duration": 1, "sections": [{"start": 0, "end": 2}]}
            ),
            lambda manifest, files: manifest["project"]["settings"].update(
                export_fps=120
            ),
            lambda manifest, files: manifest["project"].update(
                cover_settings={"size": 999}
            ),
        ):
            with (
                self.subTest(edit=edit),
                patch(
                    "apps.videomanagement.services.videos.project_import.default_storage.save"
                ) as save,
            ):
                response = self.upload(self.edited_archive(edit))
                self.assertEqual(
                    response.status_code, 400, getattr(response, "data", None)
                )
                save.assert_not_called()
        self.assertEqual(Video.objects.count(), 1)

    def test_untrusted_settings_are_not_restored(self):
        self.video.settings.update(
            voice_id=str(self.user.pk),
            retry_narration=True,
            narration_scenes=[
                {"scene_id": str(self.scene.pk), "text": "Private action"}
            ],
        )
        self.video.save(update_fields=["settings"])

        def edit(manifest, files):
            for key in ("voice_id", "retry_narration", "narration_scenes"):
                self.assertNotIn(key, manifest["project"]["settings"])
            manifest["project"]["settings"].update(
                api_key="secret",
                voice_id=str(self.user.pk),
                retry_narration=True,
                generation_params={"path": "/private"},
            )
            manifest["project"].update(
                created_by=str(self.user.pk), dir_name="/etc", voice={"path": "secret"}
            )

        response = self.upload(self.edited_archive(edit))
        self.assertEqual(response.status_code, 201, response.data)
        video = Video.objects.get(pk=response.data["id"])
        self.assertNotIn("api_key", video.settings)
        self.assertNotIn("voice_id", video.settings)
        self.assertNotIn("generation_params", video.settings)
        self.assertNotEqual(video.dir_name, "/etc")

    def test_active_content_is_rejected_even_with_matching_hash(self):
        def edit(manifest, files):
            name = next(name for name in files if name.endswith(".png"))
            files[name] = b"<html><script>alert(1)</script></html>"
            row = next(row for row in manifest["files"] if row["path"] == name)
            row.update(
                size=len(files[name]), sha256=hashlib.sha256(files[name]).hexdigest()
            )

        response = self.upload(self.edited_archive(edit))
        self.assertEqual(response.status_code, 400, response.data)

    def test_database_failure_cleans_only_new_uploads(self):
        payload = self.exported()
        with (
            patch(
                "apps.videomanagement.services.videos.project_import.Scene.objects.create",
                side_effect=RuntimeError("failed"),
            ),
        ):
            response = self.upload(payload)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(Video.objects.count(), 1)
        self.assertEqual(MediaAsset.objects.count(), 1)
        self.assertFalse(
            any(
                path.is_file()
                for path in Path(self.directory, "media", "imports").rglob("*")
            )
        )
        self.assertTrue(self.asset.file.storage.exists(self.asset.file.name))
        self.assertTrue(self.scene.file.storage.exists(self.scene.file.name))

    def test_authentication_and_upload_limits(self):
        self.client.force_authenticate(None)
        self.assertIn(self.upload(b"invalid").status_code, (401, 403))
        self.client.force_authenticate(self.user)
        with patch(
            "apps.videomanagement.serializers.project_archive.MAX_PROJECT_BYTES", 2
        ):
            self.assertEqual(self.upload(b"toolarge").status_code, 400)

    def test_symlinks_duplicate_entries_and_oversized_expansion_are_rejected(self):
        for kind in ("symlink", "duplicate", "size"):
            output = io.BytesIO()
            with ZipFile(output, "w") as bundle:
                info = ZipInfo("project.json")
                if kind == "symlink":
                    info.external_attr = 0o120777 << 16
                bundle.writestr(info, "{}")
                if kind == "duplicate":
                    bundle.writestr("project.json", "{}")
            with self.subTest(kind=kind):
                if kind == "size":
                    with patch(
                        "apps.videomanagement.services.videos.project_import.MAX_PROJECT_BYTES",
                        1,
                    ):
                        response = self.upload(output.getvalue())
                else:
                    response = self.upload(output.getvalue())
                self.assertEqual(response.status_code, 400)

    def test_resources_output_and_private_icons_survive_a_round_trip(self):
        path = Path(self.directory, "fixture.mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=blue:s=32x32:d=0.4",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(path),
            ],
            check=True,
            timeout=10,
        )
        self.video.intro = Intro.objects.create(
            created_by=self.user,
            name="Opening",
            file=ContentFile(path.read_bytes(), name="intro.mp4"),
        )
        self.video.outro = Outro.objects.create(
            created_by=self.user, name="Closing", file=self.video.intro.file.name
        )
        self.video.output = self.video.intro.file.name
        self.video.music = Music.objects.create(
            created_by=self.user,
            name="Soundtrack",
            file=self.scene.file.name,
            catalog_track=MusicCatalogTrack.objects.create(
                source_id="fixture",
                title="Track",
                category="music",
                attribution="Test artist",
                license_url="https://example.com/license",
                source_url="https://example.com/music",
            ),
        )
        self.video.source_audio = self.scene.file.name
        self.video.source_audio_duration = 1
        self.video.source_audio_words = [{"text": "Hello", "start": 0, "end": 0.5}]
        self.video.avatar = None
        icon = Icon.objects.create(
            key="custom:old",
            collection="custom",
            name="Test icon",
            created_by=self.user,
            file=self.asset.file.name,
            license="CC0",
            license_url="https://example.com/license",
            attribution="Creator",
        )
        self.scene.overlays = [
            {
                "kind": "diagram",
                "diagram": {
                    "template": "comparison",
                    "items": [
                        {"icon": icon.key, "label": "Before"},
                        {"icon": icon.key, "label": "After"},
                    ],
                },
            }
        ]
        self.video.cover = self.asset.file.name
        self.video.thumbnail = self.asset.file.name
        self.video.cover_settings = {
            "source": "upload",
            "title": "Cover title",
            "size": 8,
        }
        self.scene.overlay_logo = self.asset.file.name
        self.scene.voiceover = self.scene.file.name
        self.scene.save()
        source = video_cut_source(preview_timeline(self.video).segments)
        self.video.cuts = {
            "source_key": source["key"],
            "source_duration": source["duration"],
            "sections": [{"start": 0, "end": 0.5}],
        }
        self.video.save()
        response = self.upload(self.exported(include_output=True))
        self.assertEqual(response.status_code, 201, response.data)
        video = Video.objects.get(pk=response.data["id"])
        self.assertNotEqual(video.intro_id, self.video.intro_id)
        self.assertNotEqual(video.outro_id, self.video.outro_id)
        self.assertEqual(video.output.name, video.intro.file.name)
        self.assertEqual(video.intro.file.name, video.outro.file.name)
        self.assertEqual(video.cover.name, video.scenes.get().starting_asset.file.name)
        self.assertEqual(video.cover_settings["source"], "upload")
        self.assertEqual(video.cover_settings["title"], "Cover title")
        self.assertEqual(video.music.catalog_track.attribution, "Test artist")
        self.assertFalse(video.music.catalog_track.approved)
        self.assertEqual(video.music.created_by, self.user)
        scene = video.scenes.get()
        key = scene.overlays[0]["diagram"]["items"][0]["icon"]
        self.assertNotEqual(key, icon.key)
        self.assertEqual(Icon.objects.get(key=key).created_by, self.user)
        self.assertEqual(Icon.objects.get(key=key).attribution, "Creator")
        self.assertEqual(scene.voiceover.name, video.source_audio.name)
        self.assertEqual(scene.overlay_logo.name, scene.starting_asset.file.name)
        self.assertEqual(
            video.cuts["source_key"],
            video_cut_source(preview_timeline(video).segments)["key"],
        )

    def test_import_writes_verified_copies_to_private_r2(self):
        payload = self.exported()
        archive = MemoryR2()
        _verified.clear()
        with (
            override_settings(
                R2_STORAGE_ENABLED=True,
                R2_ACCOUNT_ID="a" * 32,
                R2_BUCKET_NAME="test-bucket",
                R2_ACCESS_KEY_ID="test",
                R2_SECRET_ACCESS_KEY="test",
                R2_JURISDICTION="",
            ),
            patch("apps.common.r2_storage._archive", return_value=archive),
        ):
            response = self.upload(payload)
            self.assertEqual(response.status_code, 201, response.data)
            video = Video.objects.get(pk=response.data["id"])
            scene = video.scenes.get()
            self.assertEqual(len(archive.objects), 2)
            for field in (scene.file, scene.starting_asset.file):
                data = archive.objects[field.storage.object_key(field.name)]
                info = field.storage.remote_info(field.name)
                self.assertEqual(
                    info["Metadata"]["sha256"], hashlib.sha256(data).hexdigest()
                )
                self.assertTrue(field.name.startswith("media/imports/"))

    def test_draft_without_media_imports_without_generation_or_rendering(self):
        draft = self.video_for(
            title="Empty draft",
            video_type="MANUAL",
            mode=None,
            settings={"narration": False},
        )
        response = self.client.get(reverse("video-export-project", args=[draft.pk]))
        self.assertEqual(response.status_code, 200)
        imported = self.upload(async_to_sync(response_bytes)(response))
        self.assertEqual(imported.status_code, 201, imported.data)
        video = Video.objects.get(pk=imported.data["id"])
        self.assertEqual(video.status, "READY")
        self.assertEqual(video.video_type, "MANUAL")
        self.assertFalse(video.scenes.exists())
        self.assertFalse(video.output)

    def test_malformed_manifest_and_nonfinite_values_are_validation_errors(self):
        for raw in (
            [],
            {"icons": [{"key": []}]},
            {"format": "viddie-project", "version": float("nan")},
            {"format": "viddie-project", "version": float("inf")},
        ):
            output = io.BytesIO()
            with ZipFile(output, "w") as bundle:
                bundle.writestr("project.json", json.dumps(raw))
            with self.subTest(manifest=raw):
                response = self.upload(output.getvalue())
                self.assertEqual(response.status_code, 400, response.data)
