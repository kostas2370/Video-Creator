import json
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse
from rest_framework.exceptions import ValidationError

from apps.series.models import VideoSeries
from apps.videomanagement import draft_tasks
from apps.videomanagement.models import Video

from .base import ApiTestCase


class IdeaTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("video-ideas")
        self.ideas = [
            {
                "title": title,
                "prompt": f"A concrete creative brief for {title}.",
            }
            for title in [
                "The Borrowed Moon",
                "The Last Lighthouse",
                "The Midnight Market",
            ]
        ]
        provider = patch(
            "apps.videomanagement.services.videos.ideas.get_reply",
            return_value=StringIO(json.dumps({"ideas": self.ideas})),
        )
        self.provider = provider.start()
        self.addCleanup(provider.stop)

    def request_ideas(self, **choices):
        return self.client.post(self.url, {"kind": "video", **choices}, format="json")

    def test_suggests_video_ideas_from_a_blank_seed_without_creating_a_project(self):
        response = self.request_ideas()
        self.assertEqual(response.status_code, 202, response.data)
        self.assertIs(
            self.draft_queue.call_args.args[0], draft_tasks.generate_ideas_task
        )
        self.provider.assert_not_called()
        self.assertEqual(self.run_draft_task(), {"ideas": self.ideas})
        self.assertEqual(self.provider.call_args.kwargs["user"], self.user)
        self.assertIn("self-contained video", self.provider.call_args.args[0])
        self.assertFalse(Video.objects.exists())
        self.assertFalse(VideoSeries.objects.exists())
        self.scene_queue.assert_not_called()

    def test_series_ideas_use_format_and_style_and_support_multiple_episodes(self):
        self.assertEqual(
            self.request_ideas(
                kind="series",
                seed="Μικροί ντετέκτιβ",
                story_format="ANIMATED_STORY",
                visual_style="Watercolor",
            ).status_code,
            202,
        )
        self.run_draft_task()
        prompt = self.provider.call_args.args[0]
        self.assertIn("repeatable series premise", prompt)
        self.assertIn("small recurring cast", prompt)
        self.assertIn("Watercolor", prompt)
        self.assertIn("Μικροί ντετέκτιβ", prompt)
        self.assertIn("language of the supplied topic", prompt)

    def test_video_preferences_and_selected_model_reach_the_worker(self):
        response = self.request_ideas(
            seed="How clouds form",
            genre="Documentary",
            target_audience="Beginners",
            gpt_model=settings.ACCEPTED_MODELS[0],
        )
        self.assertEqual(response.status_code, 202, response.data)
        self.run_draft_task()
        self.assertEqual(
            self.provider.call_args.kwargs["gpt_model"], settings.ACCEPTED_MODELS[0]
        )
        self.assertIn("Beginners", self.provider.call_args.args[0])
        self.assertIn("How clouds form", self.provider.call_args.args[0])

    def test_rejects_invalid_requests_before_queueing_a_paid_call(self):
        for choices in [
            {"kind": "unknown"},
            {"seed": "x" * 2001},
            {"story_format": "unknown"},
            {"gpt_model": "unknown-model"},
            {"visual_style": "x" * 801},
        ]:
            with self.subTest(choices=choices):
                self.assertEqual(self.request_ideas(**choices).status_code, 400)
        self.draft_queue.assert_not_called()
        self.provider.assert_not_called()

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertIn(self.request_ideas().status_code, (401, 403))
        self.draft_queue.assert_not_called()

    def test_rejects_malformed_and_duplicate_results(self):
        replies = [
            "not JSON",
            [],
            {},
            {"ideas": self.ideas[:2]},
            {"ideas": self.ideas * 2},
            {"ideas": [self.ideas[0]] * 3},
            {"ideas": [{"title": 7, "prompt": "A brief"}] + self.ideas[1:]},
            {"ideas": [{"title": "A title", "prompt": "x" * 2001}] + self.ideas[1:]},
        ]
        for reply in replies:
            with self.subTest(reply=reply):
                self.provider.return_value = StringIO(json.dumps(reply))
                self.request_ideas()
                with self.assertRaises(ValidationError):
                    self.run_draft_task()
        self.assertFalse(Video.objects.exists())

    def test_accepts_fenced_json_without_repeating_a_provider_call(self):
        self.provider.return_value = StringIO(
            "```json\n" + json.dumps({"ideas": self.ideas}) + "\n```"
        )
        self.request_ideas()
        self.assertEqual(self.run_draft_task(), {"ideas": self.ideas})
        self.provider.assert_called_once()

    def test_provider_errors_propagate_without_creating_a_project(self):
        self.provider.side_effect = RuntimeError("private provider details")
        self.request_ideas()
        with self.assertRaises(RuntimeError):
            self.run_draft_task()
        self.assertFalse(Video.objects.exists())
