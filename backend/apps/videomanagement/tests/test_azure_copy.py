import io
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.files.storage import FileSystemStorage
from django.core.management.base import CommandError
from django.db.models import FileField
from django.test import SimpleTestCase, override_settings

from apps.clips.storage import ClipStorage
from apps.common.test_azure_archive import MemoryArchive
from apps.publishing.storage import PrivateExportStorage
from apps.videomanagement.management.commands.copy_media_to_azure import (
    Command,
    registered_files,
)

MODULE = "apps.videomanagement.management.commands.copy_media_to_azure"


class AzureCopyCommandTests(SimpleTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "video.mp4").write_bytes(b"video")
        # A scan of MEDIA_ROOT would expose this. The command only accepts the
        # explicit registered file list, even though the roots overlap source.
        (self.root / ".env").write_text("secret")
        self.storage = FileSystemStorage(location=self.root)
        self.stdout, self.stderr = io.StringIO(), io.StringIO()
        self.command = Command(stdout=self.stdout, stderr=self.stderr)

    def files(self):
        return [("media", self.storage, "video.mp4")]

    def test_default_dry_run_never_connects_or_modifies_files(self):
        with (
            patch(f"{MODULE}.registered_files", return_value=self.files()),
            patch(f"{MODULE}.AzureArchive") as archive,
        ):
            self.command.handle(execute=False)
        archive.assert_not_called()
        self.assertIn("1 ready", self.stdout.getvalue())
        self.assertEqual((self.root / "video.mp4").read_bytes(), b"video")

    @override_settings(
        AZURE_STORAGE_ACCOUNT_URL="https://account.blob.core.windows.net",
        AZURE_STORAGE_CONTAINER="private",
    )
    def test_execute_copies_only_registered_files_and_can_resume(self):
        archive = MemoryArchive()
        archive.close = Mock()
        with (
            patch(f"{MODULE}.registered_files", side_effect=self.files),
            patch(f"{MODULE}.AzureArchive", return_value=archive),
        ):
            self.command.handle(execute=True)
            self.command.handle(execute=True)
        self.assertEqual(archive.files, {"media/video.mp4": b"video"})
        self.assertIn("1 copied", self.stdout.getvalue())
        self.assertIn("1 already verified", self.stdout.getvalue())

    def test_missing_files_fail_the_command(self):
        with patch(
            f"{MODULE}.registered_files",
            return_value=[("media", self.storage, "missing")],
        ):
            with self.assertRaises(CommandError):
                self.command.handle(execute=False)
        self.assertIn("1 failed", self.stdout.getvalue())

    @override_settings(
        AZURE_STORAGE_ACCOUNT_URL="https://account.blob.core.windows.net",
        AZURE_STORAGE_CONTAINER="private",
    )
    def test_connection_errors_do_not_expose_credentials(self):
        with patch(
            f"{MODULE}.AzureArchive", side_effect=RuntimeError("url?sig=secret")
        ):
            with self.assertRaises(CommandError) as result:
                self.command.handle(execute=True)
        self.assertNotIn("secret", str(result.exception))

    def test_inventory_deduplicates_each_storage_and_uses_base_manager(self):
        models = []
        for storage in (self.storage, ClipStorage(), PrivateExportStorage()):
            field = FileField(storage=storage, name="file")
            manager = Mock()
            manager.exclude.return_value.exclude.return_value.values_list.return_value.iterator.return_value = iter(
                ["video.mp4", "video.mp4"]
            )
            models.append(
                SimpleNamespace(
                    _meta=SimpleNamespace(app_label="videomanagement", fields=[field]),
                    _base_manager=manager,
                )
            )
        with patch(f"{MODULE}.apps.get_models", return_value=models):
            entries = list(registered_files())
        self.assertEqual(
            [entry[0] for entry in entries], ["media", "clips", "publishing"]
        )
