"""No network: every YouTube download is stubbed."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import music
from apps.videomanagement.models import Music
from apps.videomanagement.services.media import downloads as media
from apps.videomanagement.services.media.downloads import download_music

VIDEO_ID = "abcdefghijk"
URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"


class DownloadMusicTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        settings = override_settings(MEDIA_ROOT=self.directory.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.source = Path(self.directory.name, "download.mp4")
        self.source.write_bytes(b"original downloaded audio")
        downloader = patch.object(
            media, "download_youtube_video", return_value=(self.source, "a new song")
        )
        self.download = downloader.start()
        self.addCleanup(downloader.stop)

    def cached_music(self, **overrides):
        saved = music.make(
            **{"created_by": self.user, "youtube_video_id": VIDEO_ID, **overrides}
        )
        saved.file.save("cached.mp4", ContentFile(b"cached audio"))
        return saved

    def test_downloads_nothing_for_a_blank_url(self):
        for url in (None, "", "None"):
            with self.subTest(url=url):
                self.assertIsNone(download_music(url, user=self.user))
        self.download.assert_not_called()

    def test_reuses_the_owners_track_across_youtube_url_variants(self):
        existing = self.cached_music(name="An old title")
        for url in (
            URL,
            f"https://youtu.be/{VIDEO_ID}?t=20",
            f"https://youtube.com/shorts/{VIDEO_ID}",
        ):
            with self.subTest(url=url):
                self.assertEqual(download_music(url, user=self.user), existing)
        self.download.assert_not_called()
        self.assertEqual(Music.objects.count(), 1)

    def test_stores_a_newly_downloaded_track_with_identity_and_owner(self):
        saved = download_music(f"https://youtu.be/{VIDEO_ID}", user=self.user)
        self.assertEqual(saved.name, "a new song")
        self.assertEqual(saved.created_by, self.user)
        self.assertEqual(saved.youtube_video_id, VIDEO_ID)
        self.assertTrue(saved.file.name.endswith(".mp4"))
        self.assertEqual(Path(saved.file.path).read_bytes(), self.source.read_bytes())
        self.assertEqual(self.download.call_args.args[0], URL)
        self.assertEqual(self.download.call_args.kwargs, {"audio_only": True})
        self.assertFalse(Path(self.download.call_args.args[1]).exists())

    def test_never_reuses_another_users_track_even_for_the_same_video(self):
        other = self.cached_music(created_by=user.make())
        saved = download_music(URL, user=self.user)
        self.assertNotEqual(saved.pk, other.pk)
        self.assertEqual(saved.created_by, self.user)
        self.download.assert_called_once()

    def test_does_not_reuse_matching_titles_or_unowned_tracks(self):
        self.cached_music(name="a new song", youtube_video_id="lmnopqrstuv")
        self.cached_music(name="a new song", youtube_video_id="")
        self.cached_music(name="a new song", created_by=None)
        saved = download_music(URL, user=self.user)
        self.assertEqual(saved.youtube_video_id, VIDEO_ID)
        self.assertEqual(saved.created_by, self.user)
        self.assertEqual(Music.objects.count(), 4)
        self.download.assert_called_once()

    def test_missing_cached_file_is_replaced_without_creating_another_record(self):
        cached = music.make(
            created_by=self.user, youtube_video_id=VIDEO_ID, file="missing.mp4"
        )
        saved = download_music(URL, user=self.user)
        self.assertEqual(saved.pk, cached.pk)
        self.assertEqual(Music.objects.count(), 1)
        self.assertTrue(Path(saved.file.path).exists())

    def test_failed_download_does_not_create_a_music_record(self):
        self.download.side_effect = RuntimeError("unavailable")
        with self.assertRaisesMessage(RuntimeError, "unavailable"):
            download_music(URL, user=self.user)
        self.assertEqual(Music.objects.count(), 0)
        self.assertFalse(Path(self.download.call_args.args[1]).exists())

    def test_database_failure_deletes_the_saved_file(self):
        with patch.object(Music, "save", side_effect=RuntimeError("database failed")):
            with self.assertRaisesMessage(RuntimeError, "database failed"):
                download_music(URL, user=self.user)
        self.assertEqual(Music.objects.count(), 0)
        self.assertEqual(list(Path(self.directory.name, "media/music").glob("*")), [])
        self.assertTrue(self.source.exists())

    def test_invalid_url_and_missing_owner_are_rejected_before_downloading(self):
        with self.assertRaises(ValidationError):
            download_music("https://example.com/video", user=self.user)
        with self.assertRaises(ValueError):
            download_music(URL, user=None)
        self.download.assert_not_called()
