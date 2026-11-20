import asyncio
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from botocore.exceptions import ClientError
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.test import RequestFactory, override_settings

from apps.clips.protected_media import media_response
from apps.clips.storage import ClipStorage
from apps.common.media_archive import ArchiveError
from apps.common.r2_storage import MediaStorage, _verified
from apps.publishing.storage import PrivateExportStorage


class MemoryR2:
    bucket = "test-bucket"

    def __init__(self):
        self.objects = {}
        self.client = self
        self.requests = []

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError(
                {"ResponseMetadata": {"HTTPStatusCode": 404}}, "HeadObject"
            )
        data = self.objects[Key]
        return {
            "ContentLength": len(data),
            "ETag": '"etag"',
            "Metadata": {"sha256": hashlib.sha256(data).hexdigest()},
        }

    def get_object(self, **parameters):
        self.requests.append(parameters)
        data = self.objects[parameters["Key"]]
        if "Range" in parameters:
            start, end = parameters["Range"].removeprefix("bytes=").split("-")
            data = data[int(start) : int(end) + 1]

        class Body(io.BytesIO):
            def iter_chunks(self, chunk_size):
                while chunk := self.read(chunk_size):
                    yield chunk

        return {"Body": Body(data)}

    def upload_if_missing(self, name, source, size, digest):
        if name in self.objects:
            return False
        self.objects[name] = source.read()
        return True

    def chunks(self, name):
        yield self.objects[name]


class R2StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        config = override_settings(
            MEDIA_ROOT=self.directory.name,
            R2_STORAGE_ENABLED=True,
            R2_ACCOUNT_ID="a" * 32,
            R2_BUCKET_NAME="test-bucket",
            R2_ACCESS_KEY_ID="test",
            R2_SECRET_ACCESS_KEY="test",
            R2_JURISDICTION="",
        )
        config.enable()
        self.addCleanup(config.disable)
        self.archive = MemoryR2()
        mock = patch("apps.common.r2_storage._archive", return_value=self.archive)
        mock.start()
        self.addCleanup(mock.stop)
        _verified.clear()
        self.storage = MediaStorage()

    def test_save_uploads_verified_bytes_and_preserves_both_copies_on_delete(self):
        name = self.storage.save("media/test.mp4", ContentFile(b"video"))
        self.assertEqual(self.archive.objects["media/" + name], b"video")
        self.storage.delete(name)
        self.assertEqual(Path(self.storage.path(name)).read_bytes(), b"video")
        self.assertEqual(self.archive.objects["media/" + name], b"video")

    def test_remote_only_file_is_restored_and_checked_on_path_access(self):
        self.archive.objects["media/media/restored.mp4"] = b"from-r2"
        self.assertTrue(self.storage.exists("media/restored.mp4"))
        self.assertFalse(Path(self.directory.name, "media/restored.mp4").exists())
        with self.storage.open("media/restored.mp4") as source:
            self.assertEqual(source.read(), b"from-r2")
        self.assertEqual(self.archive.requests[-1]["IfMatch"], '"etag"')

    def test_bad_download_does_not_publish_a_corrupt_cache_file(self):
        self.archive.objects["media/corrupt"] = b"actual"
        with patch.object(
            self.archive,
            "get_object",
            return_value={
                "Body": type(
                    "Body",
                    (),
                    {
                        "iter_chunks": lambda self, **kw: iter([b"wrong"]),
                        "close": lambda self: None,
                    },
                )()
            },
        ):
            with self.assertRaises(ArchiveError):
                self.storage.path("corrupt")
        self.assertFalse(Path(self.directory.name, "corrupt").exists())
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    def test_reused_render_path_versions_remote_object_and_keeps_original(self):
        name = self.storage.save("render.mp4", ContentFile(b"first"))
        Path(self.storage.path(name)).write_bytes(b"second")
        new_name = self.storage.sync(name)
        self.assertNotEqual(name, new_name)
        self.assertEqual(self.archive.objects["media/render.mp4"], b"first")
        self.assertEqual(self.archive.objects["media/" + new_name], b"second")
        self.assertEqual(Path(self.storage.path(name)).read_bytes(), b"second")

    def test_namespaces_match_existing_copies(self):
        with override_settings(
            CLIP_STORAGE_ROOT=self.directory.name + "/clips",
            PUBLISHING_SNAPSHOT_ROOT=self.directory.name + "/publishing",
        ):
            for storage, namespace in [
                (ClipStorage(), "clips"),
                (PrivateExportStorage(), "publishing"),
            ]:
                name = storage.save("test.mp4", ContentFile(b"data"))
                self.assertEqual(self.archive.objects[namespace + "/" + name], b"data")
        with self.assertRaises(ValueError):
            PrivateExportStorage().url("secret")

    def test_remote_collision_gets_a_different_name(self):
        self.archive.objects["media/taken.mp4"] = b"old"
        name = self.storage.save("taken.mp4", ContentFile(b"new"))
        self.assertNotEqual(name, "taken.mp4")
        self.assertEqual(self.archive.objects["media/taken.mp4"], b"old")

    def test_local_mode_keeps_original_django_behavior(self):
        with override_settings(R2_STORAGE_ENABLED=False):
            name = self.storage.save("local.mp4", ContentFile(b"local"))
            self.assertEqual(self.archive.objects, {})
            self.storage.delete(name)
            self.assertFalse(Path(self.directory.name, name).exists())

    def test_local_mode_uses_django_path_validation_without_r2_checks(self):
        outside = str(Path(self.directory.name).parent / "outside-media.mp4")
        with (
            override_settings(R2_STORAGE_ENABLED=False),
            patch.object(self.storage, "object_key") as object_key,
        ):
            with self.assertRaises(SuspiciousFileOperation):
                self.storage.path(outside)
            self.assertEqual(
                self.storage.path("local.mp4"),
                str(Path(self.directory.name, "local.mp4")),
            )
        object_key.assert_not_called()

    def test_unsafe_names_cannot_access_remote_objects(self):
        for name in ("../secret", "a/../secret", "a\\secret"):
            with self.assertRaises(ArchiveError):
                self.storage.path(name)
        self.assertEqual(self.archive.requests, [])

    def test_authorized_response_streams_remote_range_without_local_download(self):
        self.archive.objects["media/remote.mp4"] = b"0123456789"
        field = SimpleNamespace(storage=self.storage, name="remote.mp4")
        response = media_response(
            RequestFactory().get("/", HTTP_RANGE="bytes=2-5"), field
        )

        async def consume():
            return b"".join([chunk async for chunk in response.streaming_content])

        self.assertEqual(asyncio.run(consume()), b"2345")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Range"], "bytes 2-5/10")
        self.assertFalse(Path(self.directory.name, "remote.mp4").exists())
        self.assertEqual(self.archive.requests[-1]["Range"], "bytes=2-5")
        head = media_response(RequestFactory().head("/"), field)
        self.assertEqual(head["Content-Length"], "10")
        bad = media_response(RequestFactory().get("/", HTTP_RANGE="bytes=99-"), field)
        self.assertEqual(bad.status_code, 416)
