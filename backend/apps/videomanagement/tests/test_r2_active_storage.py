import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.db import transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.common.r2_storage import _verified
from apps.common.test_r2_storage import MemoryR2
from apps.usermanagement.models import User
from apps.videomanagement.models import MediaAsset


@override_settings(
    R2_STORAGE_ENABLED=True,
    R2_ACCOUNT_ID="a" * 32,
    R2_BUCKET_NAME="test-bucket",
    R2_ACCESS_KEY_ID="test",
    R2_SECRET_ACCESS_KEY="test",
    R2_JURISDICTION="",
)
class ActiveR2Tests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        settings = override_settings(MEDIA_ROOT=self.directory.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.archive = MemoryR2()
        mock = patch("apps.common.r2_storage._archive", return_value=self.archive)
        mock.start()
        self.addCleanup(mock.stop)
        _verified.clear()
        self.user = User.objects.create_user(
            username="r2", email="r2@example.com", password="pass"
        )
        self.other = User.objects.create_user(
            username="other-r2", email="other-r2@example.com", password="pass"
        )

    def test_directly_generated_file_is_synced_before_database_save(self):
        path = Path(self.directory.name, "media/generated.mp4")
        path.parent.mkdir(parents=True)
        path.write_bytes(b"generated")
        asset = MediaAsset.objects.create(
            title="Generated", kind="VIDEO", file=str(path), created_by=self.user
        )
        self.assertEqual(asset.file.name, "media/generated.mp4")
        self.assertEqual(
            self.archive.objects["media/media/generated.mp4"], b"generated"
        )
        path.write_bytes(b"regenerated")
        asset.save(update_fields=["file"])
        asset.refresh_from_db()
        self.assertNotEqual(asset.file.name, "media/generated.mp4")
        self.assertEqual(
            self.archive.objects["media/media/generated.mp4"], b"generated"
        )
        self.assertEqual(
            self.archive.objects["media/" + asset.file.name], b"regenerated"
        )
        self.assertTrue(path.exists())

    def test_upload_failure_prevents_file_reference_from_being_saved(self):
        with patch.object(
            self.archive, "upload_if_missing", side_effect=OSError("offline")
        ):
            with self.assertRaises(OSError), transaction.atomic():
                MediaAsset.objects.create(
                    title="Failure",
                    kind="VIDEO",
                    file=ContentFile(b"new", name="failed.mp4"),
                    created_by=self.user,
                )
        self.assertFalse(MediaAsset.objects.filter(title="Failure").exists())
        self.assertTrue(list(Path(self.directory.name).rglob("failed.mp4")))

    def test_remote_playback_retains_ownership_checks_and_bypasses_local_acceleration(
        self,
    ):
        asset = MediaAsset.objects.create(
            title="Private",
            kind="VIDEO",
            file=ContentFile(b"0123456789", name="private.mp4"),
            created_by=self.user,
        )
        client = APIClient()
        client.force_authenticate(self.other)
        response = client.get("/" + asset.file.name)
        self.assertEqual(response.status_code, 404)
        client.force_authenticate(self.user)
        with override_settings(MEDIA_ACCEL_REDIRECT=True):
            response = client.head("/" + asset.file.name)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Length"], "10")
        self.assertNotIn("X-Accel-Redirect", response)
        self.assertIn("private", response["Cache-Control"])
