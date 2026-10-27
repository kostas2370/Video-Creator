import io
import json
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import intro, video, voice_model
from apps.videomanagement.models import SeriesEpisode, Video, VideoSeries
from apps.videomanagement.services.videos.generation import generate_video

from .base import ApiTestCase


class SeriesTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.files = tempfile.TemporaryDirectory()
        self.addCleanup(self.files.cleanup)
        storage = override_settings(MEDIA_ROOT=self.files.name)
        storage.enable()
        self.addCleanup(storage.disable)
        queue = patch("apps.videomanagement.tasks.generate_video_task.delay")
        self.queue = queue.start()
        self.addCleanup(queue.stop)
        self.series = VideoSeries.objects.create(
            created_by=self.user,
            title="Milo",
            premise="A fox learns science",
            characters="Milo wears a teal scarf",
            visual_style="Watercolor woodland",
            narration=False,
            scene_count=1,
        )

    def url(self, action="detail", series=None, episode=None):
        sid = (series or self.series).pk
        if action == "list":
            return reverse("series-list")
        if action in ("memory", "retry"):
            return reverse(
                f"series-{action}", kwargs={"pk": sid, "episode_id": episode.pk}
            )
        return reverse(f"series-{action}", args=[sid])

    def draft(self, idea="Milo discovers shadows", series=None):
        return self.client.post(
            self.url("episodes", series), {"idea": idea}, format="json"
        )

    def episode(
        self, number=1, summary="Milo built a lantern", is_canon=True, status="READY"
    ):
        project = video.make(
            created_by=self.user, status=status, settings={"creation_mode": "SERIES"}
        )
        return SeriesEpisode.objects.create(
            series=self.series,
            video=project,
            number=number,
            idea=f"Idea {number}",
            summary=summary,
            is_canon=is_canon,
        )

    def test_profile_creation_validation_and_owner_scope(self):
        other = VideoSeries.objects.create(
            created_by=user.make(),
            title="Private",
            premise="Private",
            visual_style="Ink",
            narration=False,
        )
        response = self.client.get(self.url("list"))
        self.assertEqual(
            [row["id"] for row in response.data["results"]], [str(self.series.pk)]
        )
        self.assertEqual(self.client.get(self.url(series=other)).status_code, 404)
        self.assertEqual(
            self.client.patch(self.url(series=other), {"title": "Stolen"}).status_code,
            404,
        )
        self.assertEqual(self.draft(series=other).status_code, 404)
        response = self.client.post(
            self.url("list"),
            {
                "title": "New",
                "premise": "A new world",
                "visual_style": "Ink",
                "narration": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            VideoSeries.objects.get(pk=response.data["id"]).created_by, self.user
        )
        invalid = self.client.patch(self.url(), {"scene_count": 0}, format="json")
        self.assertEqual(invalid.status_code, 400)

    def test_voice_is_required_for_consistent_narration_and_private_assets_are_scoped(
        self,
    ):
        response = self.client.patch(self.url(), {"narration": True}, format="json")
        self.assertEqual(response.status_code, 400)
        foreign_intro = intro.make(created_by=user.make())
        response = self.client.patch(
            self.url(), {"intro": str(foreign_intro.pk)}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        with patch(
            "apps.videomanagement.serializers.series.available_voice",
            return_value=voice_model.make(),
        ) as available:
            response = self.client.patch(
                self.url(),
                {"voice_model": str(voice_model.make().pk), "narration": True},
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["voice_model"], str(available.return_value.pk))

    def test_draft_snapshots_profile_before_queue_and_always_requests_review(self):
        self.queue.side_effect = lambda **kwargs: self.assertTrue(
            SeriesEpisode.objects.filter(video_id=kwargs["video_id"]).exists()
        )
        response = self.draft()
        self.assertEqual(response.status_code, 202, response.data)
        episode = SeriesEpisode.objects.get(pk=response.data["id"])
        self.assertEqual(episode.number, 1)
        self.assertEqual(episode.profile_snapshot["characters"], self.series.characters)
        self.assertTrue(self.queue.call_args.kwargs["review_script"])
        self.assertIn("teal scarf", self.queue.call_args.kwargs["series_context"])
        self.assertEqual(episode.video.settings["creation_mode"], "SERIES")
        self.client.patch(
            self.url(), {"characters": "Milo wears a red hat"}, format="json"
        )
        episode.refresh_from_db()
        self.assertEqual(
            episode.profile_snapshot["characters"], "Milo wears a teal scarf"
        )
        self.assertIn("teal scarf", episode.generation_params["series_context"])

    def test_next_episode_uses_latest_ten_completed_memories_in_order(self):
        for number in range(1, 13):
            self.episode(number=number, summary=f"Memory {number}")
        # Unreviewed drafts must not contaminate future story history.
        self.episode(
            number=13, summary="Do not remember this", is_canon=False, status="FAILED"
        )
        response = self.draft()
        self.assertEqual(response.status_code, 202, response.data)
        context = self.queue.call_args.kwargs["series_context"]
        history = json.loads(context[context.index('{"series"') :])["prior_episodes"]
        self.assertEqual([entry["number"] for entry in history], list(range(3, 13)))
        self.assertEqual(response.data["number"], 14)
        self.assertNotIn("Do not remember this", context)

    def test_in_flight_episode_blocks_another_draft(self):
        self.assertEqual(self.draft().status_code, 202)
        self.assertEqual(self.draft("Another story").status_code, 409)
        episode = self.series.episodes.get()
        episode.video.status = "REVIEW"
        episode.video.save()
        self.assertEqual(self.draft().status_code, 409)
        self.assertEqual(self.series.episodes.count(), 1)

    def test_queue_failure_keeps_retryable_episode_and_reuses_number(self):
        self.queue.side_effect = RuntimeError("queue unavailable")
        self.assertEqual(self.draft().status_code, 503)
        episode = self.series.episodes.get()
        self.assertEqual(episode.video.status, "FAILED")
        self.queue.side_effect = None
        response = self.client.post(self.url("retry", episode=episode))
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(self.series.episodes.count(), 1)
        episode.video.refresh_from_db()
        self.assertEqual(episode.video.status, "GENERATION")

    def test_episode_memory_is_owner_scoped_and_survives_video_deletion(self):
        episode = self.episode()
        response = self.client.patch(
            self.url("memory", episode=episode),
            {"summary": "Milo learned that shadows change."},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        other_series = VideoSeries.objects.create(
            created_by=user.make(),
            title="Other",
            premise="Other",
            visual_style="Ink",
            narration=False,
        )
        self.assertEqual(
            self.client.patch(
                self.url("memory", series=other_series, episode=episode),
                {"summary": "Stolen"},
                format="json",
            ).status_code,
            404,
        )
        episode.video.delete()
        episode.refresh_from_db()
        self.assertIsNone(episode.video_id)
        self.assertIn("shadows change", episode.summary)
        response = self.draft()
        self.assertEqual(response.status_code, 202, response.data)
        self.assertIn("shadows change", self.queue.call_args.kwargs["series_context"])

    def test_removing_series_preserves_episode_videos(self):
        episode = self.episode()
        vid = episode.video_id
        self.assertEqual(self.client.delete(self.url()).status_code, 204)
        self.assertTrue(Video.objects.filter(pk=vid).exists())
        self.assertFalse(SeriesEpisode.objects.filter(pk=episode.pk).exists())

    def test_episode_reference_is_a_separate_copy(self):
        content = io.BytesIO()
        Image.new("RGB", (20, 20), "red").save(content, format="PNG")
        image = SimpleUploadedFile(
            "cast.png", content.getvalue(), content_type="image/png"
        )
        response = self.client.patch(
            self.url(), {"reference_image": image}, format="multipart"
        )
        self.assertEqual(response.status_code, 200, response.data)
        response = self.draft()
        self.assertEqual(response.status_code, 202, response.data)
        episode = SeriesEpisode.objects.get(pk=response.data["id"])
        self.series.refresh_from_db()
        self.assertNotEqual(
            self.series.reference_image.name, episode.video.reference_image.name
        )
        self.assertEqual(episode.video.reference_image.read(), content.getvalue())
        # Changing the profile leaves the pending episode's copy intact.
        response = self.client.patch(
            self.url(), {"remove_reference": True}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            episode.video.reference_image.storage.exists(
                episode.video.reference_image.name
            )
        )

    def test_reference_rejects_unsupported_provider_and_missing_source(self):
        self.series.reference_image = "media/missing.png"
        self.series.save()
        response = self.client.patch(
            self.url(), {"provider": "midjourney"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response = self.draft()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.series.episodes.exists())
        self.queue.assert_not_called()

    def test_worker_stores_memory_and_review_then_marks_completed_episode_as_canon(
        self,
    ):
        response = self.draft()
        episode = SeriesEpisode.objects.get(pk=response.data["id"])
        story = {
            "title": "Milo and the shadow",
            "visual_continuity": "Milo wears a teal scarf",
            "episode_summary": "Milo moved a lantern and learned that light direction changes shadows.",
            "scenes": [{"sentences": [{"image_description": "Milo and a lantern"}]}],
        }
        with (
            patch(
                "apps.videomanagement.services.videos.generation.get_reply",
                return_value=story,
            ) as reply,
            patch(
                "apps.videomanagement.services.videos.generation.generate_directory",
                return_value=self.files.name,
            ),
            patch(
                "apps.videomanagement.services.videos.generation.VoiceModel.select_voice",
                return_value=None,
            ),
            patch(
                "apps.videomanagement.services.videos.generation.generate_scene_assets"
            ) as assets,
            patch(
                "apps.videomanagement.services.videos.generation.download_music",
                return_value=None,
            ),
        ):
            generate_video(episode.video, **episode.generation_params)
            episode.refresh_from_db()
            self.assertEqual(episode.summary, story["episode_summary"])
            self.assertFalse(episode.is_canon)
            self.assertEqual(episode.video.status, "REVIEW")
            self.assertEqual(episode.video.settings["series_id"], str(self.series.pk))
            self.assertTrue(reply.call_args.kwargs["require_episode_summary"])
            assets.assert_not_called()
            # Approval invokes generation again with the reviewed script and same snapshot.
            generate_video(
                episode.video, **{**episode.generation_params, "review_script": False}
            )
        episode.refresh_from_db()
        self.assertTrue(episode.is_canon)
        self.assertEqual(episode.video.status, "READY")

    def test_pending_video_can_finish_even_if_series_is_deleted(self):
        response = self.draft()
        episode = SeriesEpisode.objects.get(pk=response.data["id"])
        project, params = episode.video, episode.generation_params
        self.series.delete()
        with (
            patch(
                "apps.videomanagement.services.videos.generation.get_reply",
                return_value={
                    "title": "Saved episode",
                    "visual_continuity": "Fox",
                    "episode_summary": "Saved",
                    "scenes": [],
                },
            ),
            patch(
                "apps.videomanagement.services.videos.generation.generate_directory",
                return_value=self.files.name,
            ),
            patch(
                "apps.videomanagement.services.videos.generation.VoiceModel.select_voice",
                return_value=None,
            ),
        ):
            generate_video(project, **params)
        project.refresh_from_db()
        self.assertEqual(project.status, "REVIEW")

    def test_episode_lists_are_paginated_and_include_no_other_series(self):
        for number in range(1, 4):
            self.episode(number=number)
        response = self.client.get(self.url("episodes"), {"page_size": 2})
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(response.data["next"], 2)
        self.assertEqual([row["number"] for row in response.data["results"]], [3, 2])

    def test_library_filter_distinguishes_series_from_standalone_ai(self):
        episode = self.episode()
        standalone = video.make(created_by=self.user, video_type="AI", settings={})
        response = self.client.get(reverse("video-list"), {"creation_mode": "SERIES"})
        self.assertEqual(
            [row["id"] for row in response.data["results"]], [str(episode.video_id)]
        )
        response = self.client.get(reverse("video-list"), {"creation_mode": "AI"})
        self.assertEqual(
            [row["id"] for row in response.data["results"]], [str(standalone.pk)]
        )

    def test_multipart_profile_accepts_cleared_optional_selections(self):
        response = self.client.patch(
            self.url(),
            {"voice_model": "", "intro": "", "outro": "", "narration": "false"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["voice_model"])
        self.assertIsNone(response.data["intro"])

    def test_retry_does_not_claim_ready_or_deleted_episodes(self):
        episode = self.episode()
        self.assertEqual(
            self.client.post(self.url("retry", episode=episode)).status_code, 409
        )
        episode.video.delete()
        self.assertEqual(
            self.client.post(self.url("retry", episode=episode)).status_code, 400
        )

    def test_memory_updates_reject_stale_edits_and_invalid_episode_ids(self):
        episode = self.episode(summary="Original")
        url = self.url("memory", episode=episode)
        first = self.client.patch(
            url,
            {"summary": "New events", "previous_summary": "Original"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        stale = self.client.patch(
            url,
            {"summary": "Stale events", "previous_summary": "Original"},
            format="json",
        )
        self.assertEqual(stale.status_code, 409)
        episode.refresh_from_db()
        self.assertEqual(episode.summary, "New events")
        response = self.client.patch(
            url.replace(str(episode.pk), "123"), {"summary": "Invalid"}, format="json"
        )
        self.assertEqual(response.status_code, 404)
