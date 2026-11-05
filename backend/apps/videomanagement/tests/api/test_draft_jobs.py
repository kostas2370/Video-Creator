from unittest.mock import Mock, patch

from django.core import signing
from django.urls import reverse
from rest_framework.exceptions import ValidationError

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.services.draft_handlers import get_handler, register
from apps.videomanagement.services.draft_jobs import SALT
from apps.videomanagement.tasks import draft_ai_task

from .base import ApiTestCase


class DraftJobTests(ApiTestCase):
    def queue(self, route="video-draft-story", data=None, args=None):
        return self.client.post(
            reverse(route, args=args),
            data or {"prompt": "A mystery at the lighthouse"},
            format="json",
        )

    @patch.object(draft_ai_task, "apply_async")
    def test_story_queues_without_holding_request_for_provider(self, queue):
        with patch(
            "apps.videomanagement.services.videos.story.draft_story"
        ) as provider:
            response = self.queue()
        self.assertEqual(response.status_code, 202, response.data)
        provider.assert_not_called()
        self.assertNotIn("Preference-Applied", response)
        owner, task_id = signing.loads(response.data["id"], salt=SALT)
        self.assertEqual(owner, str(self.user.pk))
        self.assertEqual(queue.call_args.kwargs["task_id"], task_id)
        self.assertEqual(
            queue.call_args.kwargs["args"],
            (str(self.user.pk), "story", {"prompt": "A mystery at the lighthouse"}),
        )

    @patch.object(draft_ai_task, "apply_async")
    def test_invalid_input_and_other_users_resources_are_never_queued(self, queue):
        self.assertEqual(self.queue(data={"prompt": ""}).status_code, 400)
        other = self.video_for(owner=user.make())
        self.assertEqual(
            self.queue("video-draft-tags", args=[other.pk], data={}).status_code, 404
        )
        queue.assert_not_called()

    @patch.object(draft_ai_task, "apply_async")
    def test_video_and_series_drafts_use_the_job_contract(self, queue):
        video = self.video_for()
        cases = [
            ("video-draft-scene", [video.pk], {"prompt": "An opening scene"}, "scene"),
            ("video-draft-tags", [video.pk], {}, "tags"),
            (
                "video-youtube-description",
                [video.pk],
                {"mode": "generate"},
                "description",
            ),
            (
                "series-cast-draft",
                None,
                {
                    "premise": "Fox mysteries",
                    "visual_style": "Watercolor",
                    "story_format": "ANIMATED_STORY",
                    "count": 2,
                },
                "cast",
            ),
            (
                "series-character-description",
                None,
                {
                    "premise": "Fox mysteries",
                    "visual_style": "Watercolor",
                    "story_format": "ANIMATED_STORY",
                    "name": "Milo",
                    "idea": "A detective",
                },
                "character",
            ),
        ]
        for route, args, values, operation in cases:
            with self.subTest(operation=operation):
                response = self.queue(route, values, args)
                self.assertEqual(response.status_code, 202, response.data)
                self.assertEqual(queue.call_args.kwargs["args"][1], operation)

    @patch.object(
        draft_ai_task, "apply_async", side_effect=RuntimeError("private broker error")
    )
    def test_queue_failure_is_actionable_and_hides_internal_details(self, queue):
        response = self.queue()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private broker", str(response.data))

    @patch.object(draft_ai_task, "apply_async")
    def test_polling_is_owner_bound_and_keeps_results_private(self, queue):
        token = self.queue().data["id"]
        url = reverse("draft-job")
        with patch(
            "apps.videomanagement.services.draft_jobs.AsyncResult",
            return_value=Mock(
                state="SUCCESS",
                result={"ok": True, "data": {"story": "Reviewed result"}},
            ),
        ) as backend:
            response = self.client.get(url, {"job": token})
            self.assertEqual(
                response.data,
                {"status": "SUCCEEDED", "result": {"story": "Reviewed result"}},
            )
            self.assertEqual(response["Cache-Control"], "no-store")
            self.client.force_authenticate(user.make())
            self.assertEqual(self.client.get(url, {"job": token}).status_code, 404)
            backend.assert_called_once()
        self.assertEqual(self.client.get(url, {"job": "tampered"}).status_code, 404)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(url, {"job": token}).status_code, (401, 403))

    @patch.object(draft_ai_task, "apply_async")
    def test_states_failure_and_expiry_are_recoverable(self, queue):
        token = self.queue().data["id"]
        for state, expected in [
            ("PENDING", "QUEUED"),
            ("STARTED", "RUNNING"),
            ("FAILURE", "FAILED"),
            ("REVOKED", "FAILED"),
        ]:
            with (
                self.subTest(state=state),
                patch(
                    "apps.videomanagement.services.draft_jobs.AsyncResult",
                    return_value=Mock(
                        state=state, result=RuntimeError("private provider error")
                    ),
                ),
            ):
                response = self.client.get(reverse("draft-job"), {"job": token})
                self.assertEqual(response.data["status"], expected)
                self.assertNotIn("private provider", str(response.data))
        with patch(
            "apps.videomanagement.services.draft_jobs.signing.loads",
            side_effect=signing.SignatureExpired(),
        ):
            self.assertEqual(
                self.client.get(reverse("draft-job"), {"job": token}).status_code, 404
            )

    def test_worker_executes_the_draft_and_preserves_validation_errors(self):
        with patch(
            "apps.videomanagement.services.videos.story.draft_story",
            return_value={"story": "A draft"},
        ) as provider:
            self.assertEqual(
                draft_ai_task.run(str(self.user.pk), "story", {"prompt": "Mystery"}),
                {"ok": True, "data": {"story": "A draft"}},
            )
            provider.assert_called_once_with(self.user, prompt="Mystery")
        with patch(
            "apps.videomanagement.services.videos.story.draft_story",
            side_effect=ValidationError("The script changed. Review it first."),
        ):
            self.assertEqual(
                draft_ai_task.run(str(self.user.pk), "story", {"prompt": "Mystery"}),
                {"ok": False, "message": "The script changed. Review it first."},
            )

    def test_worker_rechecks_resource_ownership(self):
        video = self.video_for(owner=user.make())
        with patch(
            "apps.videomanagement.services.videos.tags.generate_tags"
        ) as provider:
            from apps.videomanagement.models import Video

            with self.assertRaises(Video.DoesNotExist):
                get_handler("tags")(self.user, video_id=str(video.pk))
            provider.assert_not_called()

    @patch.object(draft_ai_task, "apply_async")
    def test_async_rewrite_does_not_lock_or_modify_the_video(self, queue):
        from apps.videomanagement.baker_recipes import scene

        video = self.video_for(status="COMPLETED")
        original = scene.make(video=video, text="Original text")
        response = self.client.patch(
            reverse("scene-generate", args=[original.pk]),
            {"text": "Make it shorter"},
            format="json",
        )
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(queue.call_args.kwargs["args"][1], "rewrite")
        self.scene_queue.assert_not_called()
        video.refresh_from_db()
        original.refresh_from_db()
        self.assertEqual(video.status, "COMPLETED")
        self.assertEqual(original.text, "Original text")

    @patch.object(draft_ai_task, "apply_async")
    def test_memory_hashtags_and_transcript_search_are_queued(self, queue):
        from model_bakery import baker

        series = baker.make("series.VideoSeries", created_by=self.user)
        episode = baker.make(
            "series.SeriesEpisode", series=series, video=self.video_for()
        )
        project = baker.make(
            "clips.ClipProject",
            created_by=self.user,
            words=[{"word": "Hello", "start": 0, "end": 1}],
        )
        clip = baker.make("clips.Clip", project=project, start=0, end=15)
        cases = [
            (
                reverse(
                    "series-draft-memory",
                    kwargs={"pk": series.pk, "episode_id": episode.pk},
                ),
                {"summary": "A correction"},
                "memory",
            ),
            (
                reverse(
                    "clipproject-hashtags",
                    kwargs={"pk": project.pk, "clip_id": clip.pk},
                ),
                {},
                "hashtags",
            ),
            (
                reverse("clipproject-search-transcript", args=[project.pk]),
                {"prompt": "Find the introduction"},
                "clip_search",
            ),
        ]
        for url, values, operation in cases:
            with self.subTest(operation=operation):
                response = self.client.post(url, values, format="json")
                self.assertEqual(response.status_code, 202, response.data)
                self.assertEqual(queue.call_args.kwargs["args"][1], operation)

    def test_decorated_handlers_register_without_a_separate_operation_list(self):
        @register
        def test_registered_draft(user, *, text):
            return {"text": text}

        self.assertIs(
            get_handler(test_registered_draft.__name__), test_registered_draft
        )
        self.assertEqual(
            get_handler("test_registered_draft")(self.user, text="A draft"),
            {"text": "A draft"},
        )
        with self.assertRaisesRegex(ValueError, "already registered"):
            register(test_registered_draft)
        with self.assertRaisesRegex(ValueError, "Unknown draft handler"):
            get_handler("arbitrary.module.function")
