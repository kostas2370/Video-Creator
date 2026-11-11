from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.videomanagement.models import MediaAsset, MusicCatalogTrack
from apps.videomanagement.services.media.music_discovery import (
    TARGETS,
    DiscoveryError,
    discover,
    duration_seconds,
)


class MusicDiscoveryTests(TestCase):
    def youtube_client(self):
        pages = {}

        def get(endpoint, **params):
            if endpoint == "search":
                self.assertEqual(params["videoLicense"], "creativeCommon")
                query = params["q"]
                prefix = pages.setdefault(query, len(pages) + 1)
                offset = int(params.get("pageToken", 0)) * 50
                return {
                    "items": [
                        {"id": {"videoId": f"{prefix:03}{index:08}"}}
                        for index in range(offset, offset + 50)
                    ],
                    "nextPageToken": str(int(params.get("pageToken", 0)) + 1),
                }
            return {"items": [self.video(key) for key in params["id"].split(",")]}

        return Mock(get=Mock(side_effect=get))

    def video(self, key, license="creativeCommon", duration="PT2M"):
        return {
            "id": key,
            "status": {"license": license},
            "contentDetails": {"duration": duration},
            "snippet": {
                "title": "Music",
                "channelTitle": "Uploader",
                "tags": ["Happy", "HAPPY", " "],
                "description": "License information",
            },
        }

    def test_fills_all_six_targets_without_publishing_or_downloading_audio(self):
        counts = discover(self.youtube_client(), list(TARGETS), report=lambda _: None)
        self.assertEqual(counts, TARGETS)
        self.assertEqual(MusicCatalogTrack.objects.count(), 390)
        self.assertFalse(MusicCatalogTrack.objects.filter(approved=True).exists())
        self.assertFalse(MediaAsset.objects.exists())
        self.assertFalse(MusicCatalogTrack.objects.exclude(file="").exists())
        asset = MusicCatalogTrack.objects.first()
        self.assertEqual(asset.tags.count("happy"), 1)
        self.assertEqual(asset.metadata["declared_license"], "creativeCommon")

    def test_rerunning_a_complete_category_makes_no_requests(self):
        client = self.youtube_client()
        discover(client, ["educational"], report=lambda _: None)
        client.get.reset_mock()
        discover(client, ["educational"], report=lambda _: None)
        client.get.assert_not_called()
        self.assertEqual(MusicCatalogTrack.objects.count(), 100)

    def test_rejects_standard_license_invalid_durations_and_duplicates(self):
        client = Mock()
        client.get.side_effect = lambda endpoint, **params: (
            {"items": [{"id": {"videoId": str(i)}} for i in range(4)]}
            if endpoint == "search"
            else {
                "items": [
                    self.video("0", license="youtube"),
                    self.video("1", duration="PT20M"),
                    self.video("2", duration=""),
                    self.video("3"),
                    self.video("3"),
                ]
            }
        )
        counts = discover(client, ["fun", "horror"], report=lambda _: None)
        self.assertEqual(counts, {"fun": 1, "horror": 0})
        self.assertEqual(MusicCatalogTrack.objects.count(), 1)

    def test_api_failure_keeps_already_saved_candidates(self):
        client = self.youtube_client()
        original = client.get.side_effect

        def fail(endpoint, **params):
            if params.get("pageToken"):
                raise DiscoveryError("Quota exhausted")
            return original(endpoint, **params)

        client.get.side_effect = fail
        with self.assertRaises(DiscoveryError):
            discover(client, ["educational"], report=lambda _: None)
        self.assertEqual(MusicCatalogTrack.objects.count(), 50)
        discover(self.youtube_client(), ["educational"], report=lambda _: None)
        self.assertEqual(MusicCatalogTrack.objects.count(), 100)

    def test_duration_parsing(self):
        self.assertEqual(duration_seconds("PT1H2M3S"), 3723)
        self.assertEqual(duration_seconds("P1DT2S"), 86402)
        for invalid in ("", "P", "PT", "bad"):
            self.assertEqual(duration_seconds(invalid), 0)

    @patch.dict("os.environ", {"YOUTUBE_API_KEY": ""})
    def test_command_requires_an_api_key(self):
        with self.assertRaisesMessage(CommandError, "Set YOUTUBE_API_KEY"):
            call_command("discover_music", stdout=StringIO())
