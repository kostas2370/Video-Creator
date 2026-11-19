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
from apps.common.test_media_archive import MemoryArchive
from apps.publishing.storage import PrivateExportStorage
from apps.videomanagement.management.commands.copy_media_to_r2 import (
    Command,
    registered_files,
)

COMMAND = "apps.videomanagement.management.commands.copy_media_to_r2"
INVENTORY = f"{COMMAND}.registered_files"


@override_settings(
    R2_ACCOUNT_ID="a" * 32,
    R2_BUCKET_NAME="viddie-media",
    R2_ACCESS_KEY_ID="key",
    R2_SECRET_ACCESS_KEY="secret",
    R2_JURISDICTION="",
)
class R2CopyCommandTests(SimpleTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.root = root
        # Only registered files may be copied, even when MEDIA_ROOT includes secrets.
        (root / ".env").write_text("secret")
        self.storage = FileSystemStorage(location=root)
        self.source = root / "video.mp4"
        self.source.write_bytes(b"video")
        self.files = [("media", FileSystemStorage(location=root), "video.mp4")]
        self.output = io.StringIO()
        self.command = Command(stdout=self.output, stderr=io.StringIO())

    def test_dry_run_does_not_connect_to_r2(self):
        with (
            patch(INVENTORY, return_value=self.files),
            patch(f"{COMMAND}.R2Archive") as archive,
        ):
            self.command.handle(execute=False)
        archive.assert_not_called()
        self.assertIn("1 ready", self.output.getvalue())

    def test_execute_can_resume_without_deleting_source(self):
        archive = MemoryArchive()
        archive.close = Mock()
        with (
            patch(INVENTORY, return_value=self.files),
            patch(f"{COMMAND}.R2Archive", return_value=archive) as factory,
        ):
            self.command.handle(execute=True)
            self.command.handle(execute=True)
        factory.assert_called_with("a" * 32, "viddie-media", "key", "secret", "")
        self.assertEqual(archive.files, {"media/video.mp4": b"video"})
        self.assertEqual(self.source.read_bytes(), b"video")
        self.assertIn("1 already verified", self.output.getvalue())

    def test_errors_do_not_expose_secrets(self):
        with patch(
            f"{COMMAND}.R2Archive", side_effect=RuntimeError("signed-url-secret")
        ):
            with self.assertRaises(CommandError) as exc:
                self.command.handle(execute=True)
        self.assertIn("Cloudflare R2", str(exc.exception))
        self.assertNotIn("secret", str(exc.exception))

    def test_parallel_copy_reports_missing_files_and_keeps_all_originals(self):
        root = self.source.parent
        files = []
        for number in range(7):
            name = f"video-{number}.mp4"
            (root / name).write_bytes(f"video {number}".encode())
            files.append(("media", self.files[0][1], name))
        files.insert(2, ("media", self.files[0][1], "missing.mp4"))
        archive = MemoryArchive()
        archive.close = Mock()
        with (
            patch(INVENTORY, return_value=files),
            patch(f"{COMMAND}.R2Archive", return_value=archive),
        ):
            with self.assertRaises(CommandError):
                self.command.handle(execute=True, workers=4)
        self.assertEqual(len(archive.files), 7)
        self.assertIn("7 copied", self.output.getvalue())
        self.assertIn("1 failed", self.output.getvalue())
        self.assertTrue(
            all((root / f"video-{number}.mp4").exists() for number in range(7))
        )
        archive.close.assert_called_once()

    def test_invalid_worker_count_does_not_connect(self):
        with patch(f"{COMMAND}.R2Archive") as factory:
            with self.assertRaises(CommandError):
                self.command.handle(execute=True, workers=0)
        factory.assert_not_called()

    def test_missing_files_fail_the_dry_run(self):
        with patch(INVENTORY, return_value=[("media", self.storage, "missing")]):
            with self.assertRaises(CommandError):
                self.command.handle(execute=False)
        self.assertIn("1 failed", self.output.getvalue())

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
        with patch(f"{COMMAND}.apps.get_models", return_value=models):
            entries = list(registered_files())
        self.assertEqual(
            [entry[0] for entry in entries], ["media", "clips", "publishing"]
        )
