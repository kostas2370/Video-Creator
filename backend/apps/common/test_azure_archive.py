import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from django.core.files.storage import FileSystemStorage

from apps.common.azure_archive import (
    ArchiveError,
    AzureArchive,
    blob_name,
    copy_verified,
    local_path,
    relative_name,
)


class MemoryArchive:
    def __init__(self):
        self.files = {}

    def upload_if_missing(self, name, source, size, digest):
        if name in self.files:
            return False
        self.files[name] = source.read()
        return True

    def chunks(self, name):
        data = self.files[name]
        yield data[:3]
        yield data[3:]


class AzureArchiveTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.path = self.root / "video.mp4"
        self.path.write_bytes(b"original video content")
        self.archive = MemoryArchive()

    def test_copy_and_resume_verify_actual_bytes_and_keep_source(self):
        original = self.path.read_bytes()
        self.assertEqual(
            copy_verified(self.path, "media/video.mp4", self.archive), "copied"
        )
        self.assertEqual(
            copy_verified(self.path, "media/video.mp4", self.archive), "verified"
        )
        self.assertEqual(self.path.read_bytes(), original)

    def test_conflicting_blob_is_not_overwritten(self):
        self.archive.files["media/video.mp4"] = b"different video"
        with self.assertRaisesRegex(ArchiveError, "differs"):
            copy_verified(self.path, "media/video.mp4", self.archive)
        self.assertEqual(self.archive.files["media/video.mp4"], b"different video")

    def test_detects_corruption_after_upload(self):
        self.archive.chunks = lambda name: iter([b"corrupt"])
        with self.assertRaisesRegex(ArchiveError, "differs"):
            copy_verified(self.path, "media/video.mp4", self.archive)

    def test_detects_file_changed_during_copy(self):
        upload = self.archive.upload_if_missing

        def mutate(*args):
            result = upload(*args)
            self.path.write_bytes(b"new content")
            return result

        self.archive.upload_if_missing = mutate
        with self.assertRaisesRegex(ArchiveError, "changed"):
            copy_verified(self.path, "media/video.mp4", self.archive)

    def test_empty_files_are_verified(self):
        self.path.write_bytes(b"")
        self.assertEqual(
            copy_verified(self.path, "media/empty", self.archive), "copied"
        )

    def test_namespaces_keep_private_storages_separate(self):
        self.assertNotEqual(
            blob_name("media", "exports/a.mp4"),
            blob_name("publishing", "exports/a.mp4"),
        )

    def test_legacy_absolute_names_only_allowed_inside_storage(self):
        storage = FileSystemStorage(location=self.root)
        self.assertEqual(relative_name(storage, str(self.path)), "video.mp4")
        self.assertEqual(relative_name(storage, "media/video.mp4"), "media/video.mp4")
        for name in ("/outside/video.mp4", str(self.root / ".." / "secret")):
            with self.subTest(name=name), self.assertRaises(ArchiveError):
                relative_name(storage, name)

    def test_rejects_unsafe_names(self):
        for name in (
            "",
            "../.env",
            "/tmp/video",
            "media/../../.env",
            "media\\video",
            "a//b",
            "./a",
        ):
            with self.subTest(name=name), self.assertRaises(ArchiveError):
                blob_name("media", name)

    def test_path_validation_rejects_symlinks_and_missing_files(self):
        storage = FileSystemStorage(location=self.root)
        self.assertEqual(local_path(storage, "video.mp4"), self.path)
        (self.root / "link.mp4").symlink_to(self.path)
        (self.root / "linked").symlink_to(self.root, target_is_directory=True)
        for name in ("link.mp4", "linked/video.mp4", "missing.mp4"):
            with self.subTest(name=name), self.assertRaises(ArchiveError):
                local_path(storage, name)

    def test_remote_connection_rejects_non_https_and_embedded_credentials(self):
        for url in (
            "",
            "http://account.blob.core.windows.net",
            "https://host/?sig=secret",
            "https://user:password@host",
        ):
            with self.subTest(url=url), self.assertRaises(ArchiveError):
                AzureArchive(url, "private-media")


class AzureSDKTests(unittest.TestCase):
    """Run when the optional Azure requirements are installed; no network calls."""

    def setUp(self):
        try:
            import azure.storage.blob  # noqa: F401
            import azure.identity  # noqa: F401
        except ImportError:
            self.skipTest("Optional Azure SDK is not installed")

    def test_refuses_public_container_and_closes_clients(self):
        with (
            patch("azure.storage.blob.BlobServiceClient") as service,
            patch("azure.identity.DefaultAzureCredential") as identity,
        ):
            service.return_value.get_container_client.return_value.get_container_properties.return_value = {
                "public_access": "blob"
            }
            with self.assertRaisesRegex(ArchiveError, "public access"):
                AzureArchive("https://example.blob.core.windows.net", "media")
            service.return_value.close.assert_called_once()
            identity.return_value.close.assert_called_once()

    def test_existing_blob_upload_does_not_overwrite_and_download_is_etag_bound(self):
        from azure.core import MatchConditions
        from azure.core.exceptions import ResourceExistsError

        with (
            patch("azure.storage.blob.BlobServiceClient") as service,
            patch("azure.identity.DefaultAzureCredential"),
        ):
            container = service.return_value.get_container_client.return_value
            container.get_container_properties.return_value = {"public_access": None}
            archive = AzureArchive("https://example.blob.core.windows.net", "media")
            self.addCleanup(archive.close)
            blob = container.get_blob_client.return_value
            blob.upload_blob.side_effect = ResourceExistsError("Already exists")
            self.assertFalse(
                archive.upload_if_missing("media/a", io.BytesIO(b"a"), 1, "hash")
            )
            self.assertIs(blob.upload_blob.call_args.kwargs["overwrite"], False)
            blob.get_blob_properties.return_value = Mock(etag="version-1")
            archive.chunks("media/a")
            blob.download_blob.assert_called_once_with(
                etag="version-1", match_condition=MatchConditions.IfNotModified
            )
