import json
import tempfile
import wave
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.common.youtube import SourceImportError
from apps.videomanagement.models import MediaAsset
from apps.videomanagement.services.media.music_discovery import export_catalog


class SetupMusicCatalogTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.catalog = self.directory / "catalog.json"
        self.track = {
            "youtube_id": "abcdefghijk",
            "title": "A track",
            "category": "fun",
            "tags": ["fun"],
            "duration": 2,
            "channel_title": "Uploader",
            "declared_license": "creativeCommon",
            "discovered_at": "2026-11-11T00:00:00+00:00",
        }
        self.catalog.write_text(
            json.dumps({"schema_version": 1, "tracks": [self.track]})
        )
        self.audio = self.directory / "source.wav"
        with wave.open(str(self.audio), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(8000)
            stream.writeframes(b"\0\0" * 16000)

    def run_setup(self, **options):
        call_command(
            "setup_music_catalog",
            catalog=self.catalog,
            stdout=StringIO(),
            stderr=StringIO(),
            **options,
        )

    @patch(
        "apps.videomanagement.management.commands.setup_music_catalog.download_youtube_video"
    )
    def test_downloads_once_then_reuses_saved_audio_and_review_decisions(
        self, download
    ):
        download.return_value = (self.audio, "A track")
        self.run_setup()
        asset = MediaAsset.objects.get()
        self.assertTrue(Path(asset.file.path).exists())
        self.assertAlmostEqual(asset.duration, 2)
        self.assertFalse(asset.catalog_approved)
        self.assertTrue(asset.is_shared)
        self.assertIsNone(asset.created_by_id)
        asset.catalog_approved = True
        asset.license_url = "https://example.com/license"
        asset.tags = ["reviewed"]
        asset.save()
        self.run_setup()
        download.assert_called_once()
        self.assertEqual(
            download.call_args.args[0], "https://www.youtube.com/watch?v=abcdefghijk"
        )
        self.assertEqual(download.call_args.kwargs, {"audio_only": True})
        asset.refresh_from_db()
        self.assertTrue(asset.catalog_approved)
        self.assertEqual(asset.tags, ["reviewed"])
        self.assertEqual(MediaAsset.objects.count(), 1)

    @patch(
        "apps.videomanagement.management.commands.setup_music_catalog.download_youtube_video"
    )
    def test_repairs_a_missing_audio_file(self, download):
        download.return_value = (self.audio, "A track")
        self.run_setup()
        asset = MediaAsset.objects.get()
        Path(asset.file.path).unlink()
        self.run_setup()
        asset.refresh_from_db()
        self.assertTrue(Path(asset.file.path).exists())
        self.assertEqual(download.call_count, 2)

    @patch(
        "apps.videomanagement.management.commands.setup_music_catalog.download_youtube_video"
    )
    def test_blocked_downloads_keep_pending_metadata_and_can_be_retried(self, download):
        download.side_effect = SourceImportError("YouTube blocked the download")
        self.run_setup(best_effort=True)
        self.assertEqual(MediaAsset.objects.count(), 1)
        self.assertFalse(MediaAsset.objects.get().file)
        with self.assertRaises(CommandError):
            self.run_setup()
        download.side_effect = None
        download.return_value = (self.audio, "A track")
        self.run_setup()
        self.assertTrue(MediaAsset.objects.get().file)

    @patch(
        "apps.videomanagement.management.commands.setup_music_catalog.download_youtube_video"
    )
    def test_metadata_only_needs_no_youtube_api_key_or_download(self, download):
        self.run_setup(metadata_only=True)
        download.assert_not_called()
        self.assertEqual(MediaAsset.objects.count(), 1)

    @patch(
        "apps.videomanagement.management.commands.setup_music_catalog.download_youtube_video"
    )
    def test_rejects_invalid_manifest_before_writing_any_records(self, download):
        invalid = {**self.track, "youtube_id": "https://example.com/private"}
        self.catalog.write_text(
            json.dumps({"schema_version": 1, "tracks": [self.track, invalid]})
        )
        with self.assertRaises(CommandError):
            self.run_setup()
        download.assert_not_called()
        self.assertFalse(MediaAsset.objects.exists())

    @patch(
        "apps.videomanagement.management.commands.setup_music_catalog.download_youtube_video"
    )
    def test_failed_database_save_removes_new_audio_and_allows_retry(self, download):
        self.run_setup(metadata_only=True)
        download.return_value = (self.audio, "A track")
        before = set(self.directory.rglob("*.wav"))
        with patch.object(
            MediaAsset, "save", side_effect=RuntimeError("Database unavailable")
        ):
            self.run_setup(best_effort=True)
        self.assertFalse(MediaAsset.objects.get().file)
        self.assertEqual(set(self.directory.rglob("*.wav")), before)

    def test_exported_catalog_can_seed_a_new_database(self):
        self.run_setup(metadata_only=True)
        target = self.directory / "export.json"
        self.assertEqual(export_catalog(target), 1)
        self.assertEqual(
            json.loads(target.read_text())["tracks"][0]["youtube_id"],
            self.track["youtube_id"],
        )
        call_command(
            "setup_music_catalog", catalog=target, metadata_only=True, stdout=StringIO()
        )
        self.assertEqual(MediaAsset.objects.count(), 1)

    def test_bundled_catalog_matches_all_targets_and_has_distinct_sources(self):
        from collections import Counter
        from django.conf import settings
        from apps.videomanagement.services.media.music_discovery import TARGETS

        manifest = json.loads(
            (settings.BASE_DIR / "fixtures/music_catalog.json").read_text()
        )
        self.assertEqual(
            Counter(track["category"] for track in manifest["tracks"]), TARGETS
        )
        self.assertEqual(
            len({track["youtube_id"] for track in manifest["tracks"]}), 390
        )

    @patch(
        "apps.videomanagement.management.commands.setup_music_catalog.download_youtube_video"
    )
    def test_deployment_pauses_after_three_consecutive_download_failures(
        self, download
    ):
        tracks = [{**self.track, "youtube_id": f"{index:011}"} for index in range(4)]
        self.catalog.write_text(json.dumps({"schema_version": 1, "tracks": tracks}))
        download.side_effect = SourceImportError("YouTube blocked downloads")
        self.run_setup(best_effort=True)
        self.assertEqual(download.call_count, 3)
        self.assertEqual(MediaAsset.objects.count(), 4)
