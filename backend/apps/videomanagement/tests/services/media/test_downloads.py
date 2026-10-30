"""No network: every YouTube call is stubbed."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.videomanagement.baker_recipes import music
from apps.videomanagement.models import Music
from apps.videomanagement.services.media import downloads as media
from apps.videomanagement.services.media.downloads import download_music


class DownloadMusicTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        settings = override_settings(MEDIA_ROOT=self.directory.name)
        settings.enable()
        self.addCleanup(settings.disable)

    def test_downloads_nothing_for_a_blank_url(self):
        for url in (None, "", "None"):
            with self.subTest(url=url):
                self.assertIsNone(download_music(url))

    def test_reuses_music_that_was_already_downloaded(self):
        existing = music.make(name="a song")
        youtube = MagicMock()
        youtube.title = "a song"

        with (
            patch.object(media, "YouTube", return_value=youtube),
            patch.object(media, "download_youtube_video") as download,
        ):
            self.assertEqual(download_music("https://youtu.be/x"), existing)

        download.assert_not_called()
        self.assertEqual(Music.objects.count(), 1)

    def test_stores_a_newly_downloaded_track(self):
        youtube = MagicMock()
        youtube.title = "a new song"
        source = Path(self.directory.name, "download.mp4")
        source.write_bytes(b"original downloaded audio")

        with (
            patch.object(media, "YouTube", return_value=youtube),
            patch.object(
                media, "download_youtube_video", return_value=(source, "a new song")
            ) as download,
        ):
            music = download_music("https://youtu.be/x")

        self.assertEqual(music.name, "a new song")
        self.assertTrue(music.file.name.endswith(".mp4"))
        self.assertEqual(Path(music.file.path).read_bytes(), source.read_bytes())
        self.assertEqual(download.call_args.args[0], "https://youtu.be/x")
        self.assertEqual(download.call_args.kwargs, {"audio_only": True})
        self.assertFalse(Path(download.call_args.args[1]).exists())

    def test_failed_download_does_not_create_a_music_record(self):
        youtube = MagicMock(title="Unavailable song")
        with (
            patch.object(media, "YouTube", return_value=youtube),
            patch.object(
                media, "download_youtube_video", side_effect=RuntimeError("unavailable")
            ),
            self.assertRaisesMessage(RuntimeError, "unavailable"),
        ):
            download_music("https://youtu.be/x")
        self.assertEqual(Music.objects.count(), 0)
