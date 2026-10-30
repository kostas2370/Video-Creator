from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from apps.videomanagement.services.media.video_uploads import inspect_video_upload


class VideoUploadInspectionTests(SimpleTestCase):
    def setUp(self):
        self.upload = SimpleUploadedFile("video.mp4", b"video")
        self.metadata = {"duration": 60, "width": 1920, "height": 1080, "audio": True}

    def test_accepts_supported_video_and_returns_metadata(self):
        with patch(
            "apps.videomanagement.services.media.video_uploads.uploaded_video_metadata",
            return_value=self.metadata,
        ):
            self.assertEqual(inspect_video_upload(self.upload), self.metadata)

    def test_rejects_unsupported_extension_before_probing(self):
        with patch(
            "apps.videomanagement.services.media.video_uploads.uploaded_video_metadata"
        ) as probe:
            with self.assertRaisesMessage(ValidationError, "MP4, MOV, WebM, or M4V"):
                inspect_video_upload(SimpleUploadedFile("video.txt", b"video"))
        probe.assert_not_called()

    def test_rejects_invalid_timing_and_dimensions(self):
        for invalid in (
            {"duration": float("nan")},
            {"duration": float("inf")},
            {"duration": 0},
            {"duration": -1},
            {"width": 3841},
            {"height": 0},
        ):
            with (
                self.subTest(invalid=invalid),
                patch(
                    "apps.videomanagement.services.media.video_uploads.uploaded_video_metadata",
                    return_value={**self.metadata, **invalid},
                ),
                self.assertRaises(ValidationError),
            ):
                inspect_video_upload(self.upload)

    def test_probe_failure_returns_a_readable_validation_error(self):
        with (
            patch(
                "apps.videomanagement.services.media.video_uploads.uploaded_video_metadata",
                side_effect=ValueError("corrupt video"),
            ),
            self.assertRaisesMessage(ValidationError, "Could not read this video"),
        ):
            inspect_video_upload(self.upload)
