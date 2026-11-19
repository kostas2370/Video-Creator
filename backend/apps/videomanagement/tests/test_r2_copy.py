import io
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from django.core.files.storage import FileSystemStorage
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from apps.common.test_azure_archive import MemoryArchive
from apps.videomanagement.management.commands.copy_media_to_r2 import Command

COMMAND = "apps.videomanagement.management.commands.copy_media_to_r2"
INVENTORY = (
    "apps.videomanagement.management.commands.copy_media_to_azure.registered_files"
)


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
