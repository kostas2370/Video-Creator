from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.common.youtube import SourceImportError, download_youtube_video


class SharedYouTubeDownloadTests(SimpleTestCase):
    @patch("apps.common.youtube.YouTube")
    def test_audio_import_selects_the_highest_quality_that_fits(self, youtube):
        video = youtube.return_value
        video.length = 20
        large = MagicMock(filesize=101)
        small = MagicMock(filesize=80)
        small.download.return_value = "/unused/music.m4a"
        video.streams.filter.return_value.order_by.return_value.desc.return_value = [
            large,
            small,
        ]

        path, _title = download_youtube_video(
            "https://youtu.be/abcdefghijk", "/unused", audio_only=True, max_bytes=100
        )

        self.assertEqual(str(path), "/unused/music.m4a")
        large.download.assert_not_called()
        self.assertTrue(small.download.call_args.kwargs["filename"].endswith(".m4a"))
        video.streams.filter.assert_called_once_with(
            only_audio=True, file_extension="mp4"
        )

    @patch("apps.common.youtube.YouTube")
    def test_missing_audio_is_reported_without_downloading_video(self, youtube):
        youtube.return_value.length = 20
        youtube.return_value.streams.filter.return_value.order_by.return_value.desc.return_value = []
        with self.assertRaisesMessage(SourceImportError, "No compatible audio"):
            download_youtube_video(
                "https://youtu.be/abcdefghijk", "/unused", audio_only=True
            )

    @patch("apps.common.youtube.YouTube")
    def test_downloads_without_clips_duration_or_resolution_limits(self, youtube):
        video = youtube.return_value
        video.length = 7201
        video.title = "Long video"
        stream = MagicMock(resolution="2160p", subtype="mp4")
        stream.download.return_value = "/unused/video.mp4"
        video.streams.filter.side_effect = [[stream], []]

        path, title = download_youtube_video("https://youtu.be/abcdefghijk", "/unused")

        self.assertEqual(str(path), "/unused/video.mp4")
        self.assertEqual(title, "Long video")
        stream.download.assert_called_once()

    @patch("apps.common.youtube.time.monotonic", side_effect=[0, 601])
    @patch("apps.common.youtube.YouTube")
    def test_progress_callback_stops_a_stalled_download(self, youtube, monotonic):
        video = youtube.return_value
        video.length = 20
        stream = MagicMock(resolution="720p", subtype="mp4")
        video.streams.filter.side_effect = [[stream], []]

        def download(**kwargs):
            youtube.call_args.kwargs["on_progress_callback"](stream, b"data", 0)

        stream.download.side_effect = download
        with self.assertRaisesMessage(SourceImportError, "took too long"):
            download_youtube_video("https://youtu.be/abcdefghijk", "/unused")

    @patch("apps.common.youtube.YouTube")
    def test_unfinished_download_reports_an_import_error(self, youtube):
        video = youtube.return_value
        video.length = 20
        stream = MagicMock(resolution="720p", subtype="mp4")
        stream.download.return_value = None
        video.streams.filter.side_effect = [[stream], []]

        with self.assertRaisesMessage(SourceImportError, "did not finish"):
            download_youtube_video("https://youtu.be/abcdefghijk", "/unused")
