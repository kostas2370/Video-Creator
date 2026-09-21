"""No network: every YouTube call is stubbed."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from ...baker_recipes import music
from ...models import Music
from ...utils import media
from ...utils.media import download_music


class DownloadMusicTests(TestCase):
    def test_downloads_nothing_for_a_blank_url(self):
        for url in (None, "", "None"):
            with self.subTest(url=url):
                self.assertIsNone(download_music(url))

    def test_reuses_music_that_was_already_downloaded(self):
        existing = music.make(name="a song")
        youtube = MagicMock()
        youtube.streams.filter.return_value.first.return_value.title = "a song"

        with patch.object(media, "YouTube", return_value=youtube):
            self.assertEqual(download_music("https://youtu.be/x"), existing)

        self.assertEqual(Music.objects.count(), 1)

    def test_stores_a_newly_downloaded_track(self):
        youtube = MagicMock()
        youtube.title = "a new song"
        stream = youtube.streams.filter.return_value.first.return_value
        stream.title = "a new song"
        stream.download.return_value = "media/music/raw.webm"

        with (
            patch.object(media, "YouTube", return_value=youtube),
            patch.object(media.os, "rename"),
        ):
            music = download_music("https://youtu.be/x")

        self.assertEqual(music.name, "a new song")
        self.assertTrue(music.file.name.endswith(".mp3"))
