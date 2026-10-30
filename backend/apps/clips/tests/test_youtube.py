from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.clips.uploads import MAX_UPLOAD_BYTES
from apps.clips.youtube import SourceImportError, download_youtube


class YouTubeLimitTests(SimpleTestCase):
    def setUp(self):
        self.project = SimpleNamespace(
            youtube_url="https://www.youtube.com/watch?v=abcdefghijk", min_duration=10
        )

    @patch("apps.clips.youtube.YouTube")
    def test_duration_limit_is_checked_before_downloading(self, youtube):
        youtube.return_value.length = 7201
        with self.assertRaises(SourceImportError):
            download_youtube(self.project, "/unused")
        youtube.return_value.streams.filter.assert_not_called()

    @patch("apps.clips.youtube.YouTube")
    def test_combined_stream_sizes_are_checked_before_downloading(self, youtube):
        youtube.return_value.length = 20
        picture = MagicMock(resolution="1080p", filesize=MAX_UPLOAD_BYTES)
        audio = MagicMock(filesize=1024)
        combined, pictures, sounds = MagicMock(), MagicMock(), MagicMock()
        combined.order_by.return_value.desc.return_value.first.return_value = None
        pictures.order_by.return_value.desc.return_value.__iter__.return_value = iter(
            [picture]
        )
        sounds.order_by.return_value.desc.return_value.first.return_value = audio
        youtube.return_value.streams.filter.side_effect = [combined, pictures, sounds]
        with self.assertRaises(SourceImportError):
            download_youtube(self.project, "/unused")
        picture.download.assert_not_called()
        audio.download.assert_not_called()

    @patch("apps.clips.youtube.YouTube")
    def test_download_callback_enforces_actual_bytes(self, youtube):
        youtube.return_value.length = 20
        stream = youtube.return_value.streams.filter.return_value.order_by.return_value.desc.return_value.first.return_value
        stream.filesize = 1

        def download(**kwargs):
            progress = youtube.call_args.kwargs["on_progress_callback"]
            chunk = MagicMock()
            chunk.__len__.return_value = MAX_UPLOAD_BYTES + 1
            progress(stream, chunk, 0)

        stream.download.side_effect = download
        with self.assertRaises(SourceImportError):
            download_youtube(self.project, "/unused")
