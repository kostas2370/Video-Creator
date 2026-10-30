from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.clips.uploads import MAX_UPLOAD_BYTES
from apps.clips.youtube import SourceImportError, download_youtube, select_streams


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
        sounds = MagicMock()
        sounds.order_by.return_value.desc.return_value.first.return_value = audio
        youtube.return_value.streams.filter.side_effect = [[], [picture], sounds]
        with self.assertRaises(SourceImportError):
            download_youtube(self.project, "/unused")
        picture.download.assert_not_called()
        audio.download.assert_not_called()


class YouTubeQualityTests(SimpleTestCase):
    def select(self, combined=(), pictures=(), audio_size=100):
        video, sounds = MagicMock(), MagicMock()
        audio = SimpleNamespace(filesize=audio_size)
        sounds.order_by.return_value.desc.return_value.first.return_value = audio
        video.streams.filter.side_effect = [combined, pictures, sounds]
        return select_streams(video)

    def stream(self, resolution, size):
        return SimpleNamespace(resolution=f"{resolution}p", filesize=size)

    def test_highest_resolution_that_fits_is_selected_including_audio(self):
        high = self.stream(1080, MAX_UPLOAD_BYTES - 50)
        medium = self.stream(720, MAX_UPLOAD_BYTES // 2)
        low = self.stream(480, 1000)
        selected = self.select(pictures=[low, high, medium])
        self.assertIs(selected[0], medium)
        self.assertEqual(len(selected), 2)

    def test_selection_steps_down_to_480p_when_720p_is_too_large(self):
        high = self.stream(1080, MAX_UPLOAD_BYTES + 100)
        medium = self.stream(720, MAX_UPLOAD_BYTES)
        low = self.stream(480, 1000)
        self.assertIs(self.select(pictures=[high, medium, low])[0], low)

    def test_adaptive_high_quality_is_preferred_over_lower_combined_stream(self):
        combined = self.stream(360, 500)
        picture = self.stream(1080, 1000)
        self.assertIs(self.select(combined=[combined], pictures=[picture])[0], picture)

    def test_combined_stream_is_preferred_at_the_same_resolution(self):
        combined = self.stream(720, 500)
        picture = self.stream(720, 1000)
        self.assertEqual(
            self.select(combined=[combined], pictures=[picture]), [combined]
        )

    def test_lower_combined_stream_is_used_when_adaptive_streams_are_too_large(self):
        combined = self.stream(360, 500)
        picture = self.stream(720, MAX_UPLOAD_BYTES)
        self.assertEqual(
            self.select(combined=[combined], pictures=[picture]), [combined]
        )

    def test_videos_above_1080p_are_skipped(self):
        high = self.stream(2160, 1000)
        low = self.stream(1080, 500)
        self.assertIs(self.select(pictures=[high, low])[0], low)

    def test_oversized_combined_streams_report_that_no_resolution_fits(self):
        with self.assertRaisesMessage(SourceImportError, "lowest available resolution"):
            self.select(combined=[self.stream(360, MAX_UPLOAD_BYTES + 1)])

    def test_missing_streams_report_compatibility_error(self):
        with self.assertRaisesMessage(SourceImportError, "No compatible"):
            self.select()
