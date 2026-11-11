import os
import tempfile
from unittest.mock import Mock, patch

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import video
from apps.videomanagement.models import MediaAsset, MusicCatalogTrack
from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.services.media import music_search
from apps.videomanagement.serializers.music_search import MusicBriefSerializer

BRIEF = {
    "mood": "curious",
    "instruments": "piano",
    "tempo": "medium",
    "category": "educational",
    "query": "curious educational piano",
}


def youtube_video(video_id="abcdefghijk", **changes):
    result = {
        "id": video_id,
        "snippet": {
            "title": "Curious piano",
            "channelTitle": "Piano uploader",
            "categoryId": "10",
            "tags": ["piano", "curious"],
        },
        "status": {
            "license": "creativeCommon",
            "privacyStatus": "public",
            "embeddable": True,
        },
        "contentDetails": {"duration": "PT2M"},
    }
    result.update(changes)
    return result


class MusicSearchTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.video = video.make(created_by=self.user, status="READY")
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        client = patch.object(music_search, "youtube_client")
        self.client = client.start().return_value
        self.addCleanup(client.stop)
        self.client.get.side_effect = [
            {"items": [{"id": {"videoId": "abcdefghijk"}}]},
            {"items": [youtube_video()]},
        ]
        reply = patch.object(music_search, "creative_reply")
        self.reply = reply.start()
        self.addCleanup(reply.stop)
        self.reply.side_effect = [
            BRIEF,
            {
                "tracks": [
                    {
                        "key": "ai:abcdefghijk",
                        "reason": "Piano supports a curious lesson.",
                    }
                ]
            },
        ]

    def search(self):
        return music_search.search_music(
            self.user, prompt="A science lesson", gpt_model="gpt-4"
        )

    def test_search_creates_a_brief_ranks_actual_results_and_downloads_nothing(self):
        with patch.object(music_search, "download_music") as download:
            result = self.search()
        self.assertEqual(result["brief"], BRIEF)
        self.assertEqual(result["tracks"][0]["key"], "ai:abcdefghijk")
        self.assertIn("Piano uploader", result["tracks"][0]["attribution"])
        self.assertEqual(self.reply.call_count, 2)
        self.assertEqual(self.reply.call_args.kwargs["gpt_model"], "gpt-4")
        self.assertEqual(
            self.client.get.call_args_list[0].kwargs["videoLicense"], "creativeCommon"
        )
        self.assertEqual(
            self.client.get.call_args_list[0].kwargs["videoEmbeddable"], "true"
        )
        download.assert_not_called()
        self.assertFalse(MusicCatalogTrack.objects.exists())
        self.assertFalse(MediaAsset.objects.exists())

    def test_rejects_unknown_or_duplicate_ai_ranking_ids(self):
        for keys in (["ai:invented000"], ["ai:abcdefghijk", "ai:abcdefghijk"]):
            self.client.get.side_effect = [
                {"items": [{"id": {"videoId": "abcdefghijk"}}]},
                {"items": [youtube_video()]},
            ]
            self.reply.side_effect = [
                BRIEF,
                {"tracks": [{"key": key, "reason": "Match"} for key in keys]},
            ]
            with (
                self.subTest(keys=keys),
                self.assertRaisesMessage(ValidationError, "unknown music result"),
            ):
                self.search()

    def test_api_metadata_must_confirm_license_category_duration_and_embedding(self):
        variants = [
            {
                "status": {
                    "license": "youtube",
                    "privacyStatus": "public",
                    "embeddable": True,
                }
            },
            {
                "status": {
                    "license": "creativeCommon",
                    "privacyStatus": "private",
                    "embeddable": True,
                }
            },
            {
                "status": {
                    "license": "creativeCommon",
                    "privacyStatus": "public",
                    "embeddable": False,
                }
            },
            {
                "snippet": {
                    "title": "Podcast",
                    "channelTitle": "Uploader",
                    "categoryId": "22",
                }
            },
            {"contentDetails": {"duration": "PT16M"}},
            {"contentDetails": {"duration": "PT10S"}},
            {"snippet": {"title": "Piano", "channelTitle": "", "categoryId": "10"}},
        ]
        for values in variants:
            with self.subTest(values=values):
                self.assertIsNone(
                    music_search.youtube_candidate(youtube_video(**values))
                )

    def test_unrequested_video_ids_are_never_offered(self):
        self.client.get.side_effect = [
            {"items": [{"id": {"videoId": "abcdefghijk"}}]},
            {"items": [youtube_video("lmnopqrstuv")]},
        ]
        result = self.search()
        self.assertEqual(result["tracks"], [])
        self.assertEqual(self.reply.call_count, 1)

    def test_includes_approved_catalog_matches_and_excludes_private_media(self):
        track = MusicCatalogTrack.objects.create(
            source_id="test:local",
            title="Piano",
            category="educational",
            tags=["piano"],
            approved=True,
            license_url="https://example.com/license",
            file=ContentFile(b"audio", name="local.wav"),
        )
        self.reply.side_effect = [
            BRIEF,
            {
                "tracks": [
                    {"key": f"catalog:{track.pk}", "reason": "An existing piano match"}
                ]
            },
        ]
        result = self.search()
        self.assertEqual(result["tracks"][0]["origin"], "catalog")
        self.assertTrue(result["tracks"][0]["file"])

    def test_import_rechecks_license_before_download_and_keeps_existing_music(self):
        self.client.get.side_effect = [
            {"items": [youtube_video(status={"license": "youtube"})]}
        ]
        original = self.video.music_id
        with (
            patch.object(music_search, "set_music_from_youtube") as save,
            self.assertRaisesMessage(ValidationError, "no longer available"),
        ):
            music_search.import_search_music(self.video, "ai:abcdefghijk")
        save.assert_not_called()
        self.video.refresh_from_db()
        self.assertEqual(self.video.music_id, original)

    def test_youtube_import_is_private_and_retains_source_license_metadata(self):
        self.client.get.side_effect = [{"items": [youtube_video()]}]
        with patch.object(
            music_search, "set_music_from_youtube", return_value=self.video
        ) as save:
            result = music_search.import_search_music(self.video, "ai:abcdefghijk")
        self.assertEqual(result, self.video)
        save.assert_called_once_with(
            self.video, "https://www.youtube.com/watch?v=abcdefghijk"
        )
        source = MusicCatalogTrack.objects.get(source_id="youtube:abcdefghijk")
        self.assertFalse(source.approved)
        self.assertFalse(source.file)
        self.assertIn("Piano uploader", source.attribution)
        self.assertEqual(source.metadata["declared_license"], "creativeCommon")

    def test_rendering_video_cannot_import_a_result(self):
        self.video.status = "RENDERING"
        self.video.save()
        with self.assertRaises(VideoEditConflict):
            music_search.import_search_music(self.video, "ai:abcdefghijk")
        self.client.get.assert_not_called()


class MusicSearchConfigurationTests(TestCase):
    def test_accepts_text_or_lists_for_musical_brief_descriptors(self):
        serializer = MusicBriefSerializer(
            data={
                **BRIEF,
                "instruments": ["piano", "strings"],
                "mood": ["calm", "curious"],
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["instruments"], "piano, strings")
        self.assertEqual(serializer.validated_data["mood"], "calm, curious")

    @patch.dict(os.environ, {"YOUTUBE_API_KEY": ""})
    @patch.object(music_search, "creative_reply")
    def test_missing_youtube_key_is_reported_before_calling_ai(self, reply):
        with self.assertRaisesMessage(ValidationError, "not configured"):
            music_search.search_music(Mock(), prompt="Science")
        reply.assert_not_called()
