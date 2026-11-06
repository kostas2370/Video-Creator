import json
from unittest.mock import Mock, patch

from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery import current_app
from django.core import signing
from django.urls import reverse
from model_bakery import baker
from rest_framework.exceptions import APIException, ValidationError

from apps.usermanagement.baker_recipes import user
from apps.videomanagement import draft_tasks
from apps.videomanagement.baker_recipes import scene
from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.models import Video
from apps.videomanagement.services.draft_jobs import SALT

from .base import ApiTestCase


class DraftJobTests(ApiTestCase):
    def queue(self, data=None):
        return self.client.post(
            reverse("video-draft-story"),
            data if data is not None else {"prompt": "A mystery"},
            format="json",
        )

    def test_story_returns_an_async_task_without_running_the_provider(self):
        with patch(
            "apps.videomanagement.services.videos.story.draft_story"
        ) as provider:
            response = self.queue()
        self.assertEqual(response.status_code, 202)
        provider.assert_not_called()
        self.assertIs(self.draft_queue.call_args.args[0], draft_tasks.draft_story_task)
        owner, task_id = signing.loads(response.data["id"], salt=SALT)
        self.assertEqual(owner, str(self.user.pk))
        self.assertEqual(task_id, self.draft_queue.return_value.id)

    def test_invalid_input_and_other_users_resources_do_not_queue(self):
        self.assertEqual(self.queue({"prompt": ""}).status_code, 400)
        other = self.video_for(owner=user.make())
        self.assertEqual(
            self.client.post(
                reverse("video-draft-tags", args=[other.pk]), {}, format="json"
            ).status_code,
            404,
        )
        self.draft_queue.assert_not_called()

    def test_endpoints_queue_their_own_celery_tasks(self):
        video = self.video_for(status="COMPLETED")
        line = scene.make(video=video)
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
                "post",
                reverse("video-draft-scene", args=[video.pk]),
                {"prompt": "An opening"},
                draft_tasks.draft_scene_task,
            ),
            (
                "post",
                reverse("video-draft-tags", args=[video.pk]),
                {},
                draft_tasks.draft_tags_task,
            ),
            (
                "post",
                reverse("video-generate-tags", args=[video.pk]),
                {"previous_tags": {}},
                draft_tasks.generate_tags_task,
            ),
            (
                "post",
                reverse("video-youtube-description", args=[video.pk]),
                {"mode": "generate"},
                draft_tasks.draft_description_task,
            ),
            (
                "patch",
                reverse("scene-generate", args=[line.pk]),
                {"text": "Make it shorter"},
                draft_tasks.rewrite_scene_task,
            ),
            (
                "post",
                reverse("series-cast-draft"),
                {
                    "premise": "Fox mysteries",
                    "visual_style": "Watercolor",
                    "story_format": "ANIMATED_STORY",
                    "count": 2,
                },
                draft_tasks.draft_cast_task,
            ),
            (
                "post",
                reverse("series-character-description"),
                {
                    "premise": "Fox mysteries",
                    "visual_style": "Watercolor",
                    "story_format": "ANIMATED_STORY",
                    "name": "Milo",
                    "idea": "A detective",
                },
                draft_tasks.draft_character_task,
            ),
            (
                "post",
                reverse(
                    "series-draft-memory",
                    kwargs={"pk": series.pk, "episode_id": episode.pk},
                ),
                {"summary": "A correction"},
                draft_tasks.draft_memory_task,
            ),
            (
                "post",
                reverse(
                    "clipproject-hashtags",
                    kwargs={"pk": project.pk, "clip_id": clip.pk},
                ),
                {},
                draft_tasks.draft_hashtags_task,
            ),
            (
                "post",
                reverse("clipproject-search-transcript", args=[project.pk]),
                {"prompt": "Find the introduction"},
                draft_tasks.search_transcript_task,
            ),
        ]
        for method, url, values, task in cases:
            with self.subTest(task=task.name):
                response = getattr(self.client, method)(url, values, format="json")
                self.assertEqual(response.status_code, 202, response.data)
                self.assertIs(self.draft_queue.call_args.args[0], task)
        video.refresh_from_db()
        self.assertEqual(video.status, "COMPLETED")

    def test_queue_failure_returns_503_without_exposing_broker_details(self):
        self.draft_queue.side_effect = RuntimeError("private broker details")
        response = self.queue()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private broker", str(response.data))

    def test_status_requires_owner_and_signed_token(self):
        token = self.queue().data["id"]
        url = reverse("draft-job")
        with patch(
            "apps.videomanagement.services.draft_jobs.AsyncResult",
            return_value=Mock(state="SUCCESS", result={"story": "A draft"}),
        ) as backend:
            response = self.client.get(url, {"job": token})
            self.assertEqual(
                response.data, {"status": "SUCCEEDED", "result": {"story": "A draft"}}
            )
            self.assertEqual(response["Cache-Control"], "no-store")
            self.client.force_authenticate(user.make())
            self.assertEqual(self.client.get(url, {"job": token}).status_code, 404)
            backend.assert_called_once()
        self.assertEqual(self.client.get(url, {"job": "tampered"}).status_code, 404)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(url, {"job": token}).status_code, (401, 403))

    def test_pending_failure_and_expired_tasks(self):
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
                        state=state, result=RuntimeError("private provider details")
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

    def test_worker_returns_provider_result_and_propagates_failure(self):
        with patch(
            "apps.videomanagement.services.videos.story.draft_story",
            return_value={"story": "A draft"},
        ):
            self.assertEqual(
                draft_tasks.draft_story_task.run(str(self.user.pk), prompt="Mystery"),
                {"story": "A draft"},
            )
        with patch(
            "apps.videomanagement.services.videos.story.draft_story",
            side_effect=ValidationError("The script changed"),
        ):
            with self.assertRaises(ValidationError):
                draft_tasks.draft_story_task.run(str(self.user.pk), prompt="Mystery")

    def test_worker_rechecks_resource_ownership(self):
        video = self.video_for(owner=user.make())
        with patch(
            "apps.videomanagement.services.videos.tags.generate_tags"
        ) as provider:
            with self.assertRaises(Video.DoesNotExist):
                draft_tasks.draft_tags_task.run(
                    str(self.user.pk), video_id=str(video.pk)
                )
            provider.assert_not_called()

    def test_task_errors_survive_celery_serialization_without_leaking_provider_details(
        self,
    ):
        token = self.queue().data["id"]
        cases = [
            (
                ValidationError("Add a script before generating."),
                "Add a script before generating.",
            ),
            (
                ValidationError(
                    {"cast": [{"appearance": ["Describe the character."]}]}
                ),
                "cast: appearance: Describe the character.",
            ),
            (
                ValidationError({"non_field_errors": ["Review the current script."]}),
                "Review the current script.",
            ),
            (
                VideoEditConflict(
                    {
                        "detail": "The script changed. Refresh and try again.",
                        "tags": ["private metadata"],
                    }
                ),
                "The script changed. Refresh and try again.",
            ),
            (
                SoftTimeLimitExceeded("private worker details"),
                "Generation took too long. Please try again.",
            ),
            (
                TimeLimitExceeded("private worker details"),
                "Generation took too long. Please try again.",
            ),
            (
                APIException("private provider credential"),
                "Could not generate this draft. Please try again.",
            ),
            (
                RuntimeError("private provider URL"),
                "Could not generate this draft. Please try again.",
            ),
        ]
        backend = current_app.backend
        for error, expected in cases:
            with self.subTest(error=type(error).__name__):
                # Exercise Celery's actual JSON exception round trip, not just a mock exception.
                serialized = json.loads(
                    json.dumps(backend.encode_result(error, "FAILURE"))
                )
                restored = backend.exception_to_python(serialized)
                with patch(
                    "apps.videomanagement.services.draft_jobs.AsyncResult",
                    return_value=Mock(state="FAILURE", result=restored),
                ):
                    response = self.client.get(reverse("draft-job"), {"job": token})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, {"status": "FAILED", "error": expected})
                self.assertNotIn("private", str(response.data))

    def test_revoked_task_has_an_actionable_message(self):
        token = self.queue().data["id"]
        with patch(
            "apps.videomanagement.services.draft_jobs.AsyncResult",
            return_value=Mock(state="REVOKED", result=RuntimeError("private details")),
        ):
            response = self.client.get(reverse("draft-job"), {"job": token})
        self.assertEqual(
            response.data,
            {
                "status": "FAILED",
                "error": "Generation was cancelled or expired. Please try again.",
            },
        )
