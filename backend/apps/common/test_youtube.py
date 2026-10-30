from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.common.youtube import SourceImportError, download_youtube_video


class SharedYouTubeDownloadTests(SimpleTestCase):
    @patch("apps.common.youtube.YouTube")
    def test_audio_mode_downloads_the_best_mp4_audio(self, youtube):
        video = youtube.return_value
        video.title = "My song"
        stream = video.streams.filter.return_value.order_by.return_value.desc.return_value.first.return_value
        stream.subtype = "mp4"
        stream.download.return_value = "/unused/music.mp4"

        path, title = download_youtube_video(
            "https://youtu.be/abcdefghijk", "/unused", audio_only=True
        )

        self.assertEqual(str(path), "/unused/music.mp4")
        self.assertEqual(title, "My song")
        video.streams.filter.assert_called_once_with(
            only_audio=True, file_extension="mp4"
        )
        video.streams.get_highest_resolution.assert_not_called()

    @patch("apps.common.youtube.YouTube")
    def test_missing_audio_is_reported_without_downloading_video(self, youtube):
        youtube.return_value.streams.filter.return_value.order_by.return_value.desc.return_value.first.return_value = None
        with self.assertRaisesMessage(SourceImportError, "No compatible media"):
            download_youtube_video(
                "https://youtu.be/abcdefghijk", "/unused", audio_only=True
            )

    @patch("apps.common.youtube.YouTube")
    def test_video_mode_uses_library_selection_timeouts_and_retries(self, youtube):
        video = youtube.return_value
        video.title = "Long video"
        stream = MagicMock(subtype="mp4")
        stream.download.return_value = "/unused/video.mp4"
        video.streams.get_highest_resolution.return_value = stream

        path, title = download_youtube_video("https://youtu.be/abcdefghijk", "/unused")

        self.assertEqual(str(path), "/unused/video.mp4")
        self.assertEqual(title, "Long video")
        youtube.assert_called_once_with("https://youtu.be/abcdefghijk")
        self.assertEqual(stream.download.call_args.kwargs["timeout"], 30)
        self.assertEqual(stream.download.call_args.kwargs["max_retries"], 1)

    @patch("apps.common.youtube.YouTube")
    def test_unfinished_download_reports_an_import_error(self, youtube):
        stream = youtube.return_value.streams.get_highest_resolution.return_value
        stream.subtype = "mp4"
        stream.download.return_value = None
        with self.assertRaisesMessage(SourceImportError, "did not finish"):
            download_youtube_video("https://youtu.be/abcdefghijk", "/unused")
