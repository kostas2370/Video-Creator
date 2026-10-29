import io
import json
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.series.models import SeriesEpisode, VideoSeries
from apps.series.serializers import (
    EpisodeDraftSerializer,
    VideoSeriesSerializer,
    validate_episode_generation,
)
from apps.series.services import draft_episode, retry_episode
from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import (
    intro,
    outro,
    scene,
    scene_image,
    video,
    voice_model,
)
from apps.videomanagement.exceptions import (
    GenerationQueueUnavailable,
    VideoEditConflict,
)
from apps.videomanagement.models import Video
from apps.videomanagement.services.videos.generation import generate_video
from apps.videomanagement.tests.api.base import ApiTestCase


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
        if action in ("memory", "retry", "draft-memory"):
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
        episode = SeriesEpisode.objects.create(
            series=self.series,
            video=project,
            number=number,
            idea=f"Idea {number}",
            summary=summary,
            is_canon=is_canon,
        )
        episode.memory_source_hash = episode.script_hash
        episode.save(update_fields=["memory_source_hash"])
        return episode

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
            "apps.series.serializers.available_voice",
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

    def test_retry_keeps_validated_settings_after_another_queue_failure(self):
        self.queue.side_effect = RuntimeError("queue unavailable")
        self.assertEqual(self.draft().status_code, 503)
        episode = self.series.episodes.get()
        params = {**episode.generation_params, "scene_count": 3}
        with self.assertRaises(GenerationQueueUnavailable):
            retry_episode(episode, generation_params=params, owner=self.user)
        episode.refresh_from_db()
        episode.video.refresh_from_db()
        self.assertEqual(episode.generation_params, params)
        self.assertEqual(
            episode.video.settings["generation_params"],
            {**params, "review_script": False},
        )
        self.assertEqual(episode.video.status, "FAILED")

        self.queue.side_effect = None
        response = self.client.post(self.url("retry", episode=episode))
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(self.queue.call_args.kwargs["scene_count"], 3)
        self.assertEqual(
            self.queue.call_args.kwargs["series_context"], params["series_context"]
        )
        self.assertEqual(self.series.episodes.count(), 1)

    def test_retry_returns_conflict_if_video_is_deleted_after_validation(self):
        self.queue.side_effect = RuntimeError("queue unavailable")
        self.assertEqual(self.draft().status_code, 503)
        episode = self.series.episodes.get()
        self.queue.side_effect = None
        self.queue.reset_mock()

        def delete_video_before_retry(*args):
            episode.video.delete()
            return dict(episode.generation_params)

        with patch(
            "apps.series.views.validate_episode_generation",
            side_effect=delete_video_before_retry,
        ):
            response = self.client.post(self.url("retry", episode=episode))
        self.assertEqual(response.status_code, 409, response.data)
        self.assertIn("no longer available", str(response.data))
        self.queue.assert_not_called()
        episode.refresh_from_db()
        self.assertIsNone(episode.video_id)

    def test_draft_failure_cleans_only_the_copied_reference_and_preserves_error(self):
        for cleanup_fails in (False, True):
            with self.subTest(cleanup_fails=cleanup_fails):
                self.series.reference_image.save(
                    "reference.png", ContentFile(b"reference")
                )
                original_name = self.series.reference_image.name
                storage = self.series.reference_image.storage
                failure = RuntimeError("episode insert failed")
                with (
                    patch.object(SeriesEpisode.objects, "create", side_effect=failure),
                    patch.object(
                        storage,
                        "delete",
                        wraps=storage.delete,
                        side_effect=OSError("storage unavailable")
                        if cleanup_fails
                        else None,
                    ) as delete,
                    patch("apps.series.services.logger") as logger,
                    self.assertRaises(RuntimeError) as raised,
                ):
                    draft_episode(
                        self.series,
                        idea="Shadows",
                        generation_params={"review_script": True},
                        owner=self.user,
                    )
                self.assertIs(raised.exception, failure)
                delete.assert_called_once()
                copied_name = delete.call_args.args[0]
                self.assertNotEqual(copied_name, original_name)
                self.assertEqual(storage.exists(copied_name), cleanup_fails)
                self.assertTrue(storage.exists(original_name))
                self.assertEqual(logger.exception.call_count, int(cleanup_fails))
                self.assertFalse(self.series.episodes.exists())
                self.assertFalse(Video.objects.filter(created_by=self.user).exists())
                self.queue.assert_not_called()

    def test_episode_memory_is_owner_scoped_and_survives_video_deletion(self):
        episode = self.episode()
        response = self.client.patch(
            self.url("memory", episode=episode),
            {
                "summary": "Milo learned that shadows change.",
                "previous_summary": episode.summary,
                "script_hash": episode.script_hash,
            },
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

    def test_memory_save_requires_both_conflict_checks(self):
        episode = self.episode(summary="Original")
        data = {
            "summary": "New events",
            "previous_summary": "Original",
            "script_hash": episode.script_hash,
        }
        for missing in ("previous_summary", "script_hash"):
            with self.subTest(missing=missing):
                response = self.client.patch(
                    self.url("memory", episode=episode),
                    {key: value for key, value in data.items() if key != missing},
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn(missing, response.data)
        for invalid in (
            None,
            "invalid",
            " " + episode.script_hash,
            episode.script_hash + "\n",
        ):
            with self.subTest(script_hash=invalid):
                response = self.client.patch(
                    self.url("memory", episode=episode),
                    {**data, "script_hash": invalid},
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
        response = self.client.patch(
            self.url("memory", episode=episode),
            {**data, "script_hash": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 409, response.data)
        episode.refresh_from_db()
        self.assertEqual(episode.summary, "Original")

    def test_deleted_episode_memory_can_be_saved_with_its_last_fingerprint(self):
        episode = self.episode(summary="Original")
        episode.video.delete()
        episode.refresh_from_db()
        data = {
            "summary": "Corrected",
            "previous_summary": "Original",
            "script_hash": episode.script_hash,
        }
        response = self.client.patch(
            self.url("memory", episode=episode), data, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["summary"], "Corrected")
        self.assertIsNone(response.data["video_id"])

    def test_generation_validation_normalizes_asset_uuids_without_mutating_choices(
        self,
    ):
        opening = intro.make(created_by=self.user)
        ending = outro.make(created_by=self.user)
        choices = {
            "message": "Shadows",
            "narration": False,
            "intro": opening.pk,
            "outro": ending.pk,
        }
        params = validate_episode_generation(
            choices, {"request": SimpleNamespace(user=self.user)}
        )
        self.assertEqual(params["intro"], str(opening.pk))
        self.assertEqual(params["outro"], str(ending.pk))
        self.assertEqual(choices["intro"], opening.pk)
        self.assertEqual(choices["outro"], ending.pk)

    def test_memory_updates_reject_stale_edits_and_invalid_episode_ids(self):
        episode = self.episode(summary="Original")
        url = self.url("memory", episode=episode)
        first = self.client.patch(
            url,
            {
                "summary": "New events",
                "previous_summary": "Original",
                "script_hash": episode.script_hash,
            },
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        stale = self.client.patch(
            url,
            {
                "summary": "Stale events",
                "previous_summary": "Original",
                "script_hash": episode.script_hash,
            },
            format="json",
        )
        self.assertEqual(stale.status_code, 409)
        episode.refresh_from_db()
        self.assertEqual(episode.summary, "New events")
        response = self.client.patch(
            url.replace(str(episode.pk), "123"), {"summary": "Invalid"}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_serializing_profile_asset_ids_does_not_fetch_each_related_asset(self):
        voice = voice_model.make()
        opening = intro.make(created_by=self.user)
        ending = outro.make(created_by=self.user)
        for number in range(3):
            VideoSeries.objects.create(
                created_by=self.user,
                title=f"Profile {number}",
                premise="A world",
                visual_style="Ink",
                voice_model_id=voice.pk,
                intro_id=opening.pk,
                outro_id=ending.pk,
            )
        profiles = list(VideoSeries.objects.filter(voice_model_id=voice.pk))
        with self.assertNumQueries(0):
            data = VideoSeriesSerializer(profiles, many=True).data
        self.assertEqual(len(data), 3)
        self.assertTrue(all(row["voice_model"] == str(voice.pk) for row in data))

    def test_queue_failure_does_not_overwrite_worker_progress(self):
        def worker_progress_then_dispatch_error(**params):
            Video.objects.filter(pk=params["video_id"]).update(status="REVIEW")
            raise RuntimeError("Acknowledgement lost after worker received the task")

        self.queue.side_effect = worker_progress_then_dispatch_error
        self.assertEqual(self.draft().status_code, 503)
        episode = self.series.episodes.get()
        self.assertEqual(episode.video.status, "REVIEW")

    def test_changed_profile_is_rejected_between_validation_and_snapshot(self):
        serializer = EpisodeDraftSerializer(
            data={"idea": "A discovery"},
            context={"request": SimpleNamespace(user=self.user), "series": self.series},
        )
        serializer.is_valid(raise_exception=True)
        VideoSeries.objects.filter(pk=self.series.pk).update(
            characters="Different cast", updated_at=timezone.now()
        )
        with self.assertRaises(VideoEditConflict):
            draft_episode(self.series, owner=self.user, **serializer.validated_data)
        self.assertFalse(self.series.episodes.exists())
        self.queue.assert_not_called()

    def test_memory_save_can_be_replayed_after_a_lost_response(self):
        episode = self.episode(summary="Original")
        data = {
            "summary": "New memory",
            "previous_summary": "Original",
            "script_hash": episode.script_hash,
        }
        for _ in range(2):
            response = self.client.patch(
                self.url("memory", episode=episode), data, format="json"
            )
            self.assertEqual(response.status_code, 200, response.data)
        episode.refresh_from_db()
        self.assertEqual(episode.summary, "New memory")

    def test_active_episode_is_available_outside_visible_page(self):
        active = self.episode(number=1, status="REVIEW")
        for number in range(2, 27):
            self.episode(number=number)
        profile = self.client.get(self.url()).data
        self.assertEqual(str(profile["active_episode"]["id"]), str(active.pk))
        self.assertEqual(
            str(profile["active_episode"]["video_id"]), str(active.video_id)
        )
        rows = self.client.get(self.url("episodes")).data["results"]
        self.assertNotIn(str(active.pk), [row["id"] for row in rows])
        active.video.status = "READY"
        active.video.save(update_fields=["status"])
        self.assertIsNone(self.client.get(self.url()).data["active_episode"])

    def test_memory_requires_review_after_story_edit_and_rejects_stale_save(self):
        episode = self.episode()
        line = scene.make(video=episode.video, text="Milo found a lantern")
        visual = scene_image.make(scene=line, prompt="Milo holding a lantern")
        episode.__dict__.pop("script_snapshot", None)
        episode.memory_source_hash = episode.script_hash
        episode.save(update_fields=["memory_source_hash"])
        old_hash = episode.script_hash
        line.text = "Milo lost his lantern"
        line.save(update_fields=["text"])
        response = self.client.get(self.url("episodes"))
        row = response.data["results"][0]
        self.assertTrue(row["memory_needs_review"])
        self.assertTrue(row["can_update_memory"])
        url = self.url("memory", episode=episode)
        stale = self.client.patch(
            url,
            {
                "summary": "Milo lost a lantern",
                "script_hash": old_hash,
                "previous_summary": episode.summary,
            },
            format="json",
        )
        self.assertEqual(stale.status_code, 409)
        saved = self.client.patch(
            url,
            {
                "summary": "Milo lost a lantern",
                "script_hash": row["script_hash"],
                "previous_summary": episode.summary,
            },
            format="json",
        )
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assertFalse(saved.data["memory_needs_review"])
        visual.prompt = "Milo looking for his lantern"
        visual.save(update_fields=["prompt"])
        self.assertTrue(
            self.client.get(self.url("episodes")).data["results"][0][
                "memory_needs_review"
            ]
        )

    @patch(
        "apps.series.services.get_update_sentence",
        return_value="Milo found a blue lantern.",
    )
    def test_memory_update_is_an_unsaved_draft_and_includes_manual_corrections(
        self, ai
    ):
        episode = self.episode(summary="Manual facts")
        scene.make(video=episode.video, text="Milo found a lantern")
        response = self.client.post(
            self.url("draft-memory", episode=episode),
            {"summary": "The lantern was blue"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["summary"], "Milo found a blue lantern.")
        self.assertIn("The lantern was blue", ai.call_args.args[0])
        self.assertIn("Milo found a lantern", ai.call_args.args[0])
        episode.refresh_from_db()
        self.assertEqual(episode.summary, "Manual facts")
        episode.__dict__.pop("script_snapshot", None)
        self.assertEqual(response.data["script_hash"], episode.script_hash)

    @patch(
        "apps.series.services.get_update_sentence",
        return_value="",
    )
    def test_invalid_memory_draft_preserves_saved_memory(self, ai):
        episode = self.episode()
        scene.make(video=episode.video)
        response = self.client.post(
            self.url("draft-memory", episode=episode), {}, format="json"
        )
        self.assertEqual(response.status_code, 500)
        episode.refresh_from_db()
        self.assertEqual(episode.summary, "Milo built a lantern")

    @patch("apps.series.services.get_update_sentence")
    def test_memory_update_rejects_changes_during_generation(self, ai):
        episode = self.episode()
        line = scene.make(video=episode.video, text="Before")

        def change_script(*args, **kwargs):
            line.text = "After"
            line.save(update_fields=["text"])
            return "Before summary"

        ai.side_effect = change_script
        response = self.client.post(
            self.url("draft-memory", episode=episode), {}, format="json"
        )
        self.assertEqual(response.status_code, 409)
        episode.refresh_from_db()
        self.assertEqual(episode.summary, "Milo built a lantern")

    def test_unreviewed_memory_is_excluded_from_new_episode_context(self):
        episode = self.episode()
        scene.make(video=episode.video, text="A changed story")
        response = self.draft()
        self.assertEqual(response.status_code, 202, response.data)
        self.assertNotIn(
            "Milo built a lantern", self.queue.call_args.kwargs["series_context"]
        )

    def test_storyboard_and_generated_rows_share_memory_fingerprint(self):
        episode = self.episode(status="REVIEW")
        episode.video.gpt_answer = {
            "scenes": [
                {
                    "sentences": [
                        {
                            "sentence": "Milo found a lantern",
                            "image_description": "A blue lantern",
                        }
                    ]
                }
            ]
        }
        episode.video.save(update_fields=["gpt_answer"])
        episode.__dict__.pop("script_snapshot", None)
        original = episode.script_hash
        episode.memory_source_hash = original
        episode.save(update_fields=["memory_source_hash"])
        line = scene.make(video=episode.video, text="Milo found a lantern")
        scene_image.make(scene=line, prompt="A blue lantern")
        episode.video.status = "READY"
        episode.video.save(update_fields=["status"])
        episode = SeriesEpisode.objects.select_related("video").get(pk=episode.pk)
        self.assertEqual(episode.script_hash, original)
        self.assertFalse(episode.memory_needs_review)
        line.motion_style = "NONE"
        line.pause_after = 2
        line.save(update_fields=["motion_style", "pause_after"])
        self.assertFalse(SeriesEpisode.objects.get(pk=episode.pk).memory_needs_review)
        line.archived_at = timezone.now()
        line.save(update_fields=["archived_at"])
        self.assertTrue(SeriesEpisode.objects.get(pk=episode.pk).memory_needs_review)

    @patch("apps.series.services.get_update_sentence")
    def test_memory_update_is_owner_scoped_and_requires_current_script(self, ai):
        episode = self.episode()
        other = VideoSeries.objects.create(
            created_by=user.make(), title="Other", premise="Private", visual_style="Ink"
        )
        response = self.client.post(
            self.url("draft-memory", series=other, episode=episode), {}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        episode.video.delete()
        response = self.client.post(
            self.url("draft-memory", episode=episode), {}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        ai.assert_not_called()
