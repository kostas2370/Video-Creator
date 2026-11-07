import json
from io import StringIO
from unittest.mock import patch

from django.urls import reverse
from rest_framework.exceptions import ValidationError

from apps.videomanagement import draft_tasks
from apps.videomanagement.models import Video

from .base import ApiTestCase


class PromptRewriteTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("video-rewrite-prompt")
        provider = patch("apps.videomanagement.services.videos.ideas.get_reply")
        self.provider = provider.start()
        self.addCleanup(provider.stop)
        self.provider.return_value = StringIO(
            json.dumps({"prompt": "Milo discovers a lantern at dusk."})
        )

    def request_rewrite(self, **choices):
        return self.client.post(
            self.url,
            {"kind": "video", "prompt": "Milo finds a lantern", **choices},
            format="json",
        )

    def test_queues_a_reviewable_rewrite_without_creating_or_changing_media(self):
        response = self.request_rewrite(instructions="Make it more visual")
        self.assertEqual(response.status_code, 202, response.data)
        self.assertIs(
            self.draft_queue.call_args.args[0], draft_tasks.rewrite_prompt_task
        )
        self.provider.assert_not_called()
        self.assertEqual(
            self.run_draft_task(), {"prompt": "Milo discovers a lantern at dusk."}
        )
        self.assertEqual(self.provider.call_args.kwargs["user"], self.user)
        self.assertIn("Make it more visual", self.provider.call_args.args[0])
        self.assertFalse(Video.objects.exists())
        self.scene_queue.assert_not_called()

    def test_routes_video_series_and_visual_prompts_with_appropriate_guidance(self):
        for kind, expected in [
            ("video", "creative brief"),
            ("series", "repeatable series"),
            ("visual", "one achievable action"),
        ]:
            with self.subTest(kind=kind):
                self.request_rewrite(kind=kind)
                self.run_draft_task()
                self.assertIn(expected, self.provider.call_args.args[0])
                self.assertIn(
                    "Preserve the user's core intent", self.provider.call_args.args[0]
                )

    def test_invalid_requests_never_queue_a_paid_call(self):
        for choices in [
            {"kind": "bad"},
            {"prompt": ""},
            {"prompt": " "},
            {"prompt": "x" * 2001},
            {"instructions": "x" * 501},
        ]:
            with self.subTest(choices=choices):
                self.assertEqual(self.request_rewrite(**choices).status_code, 400)
        self.draft_queue.assert_not_called()
        self.provider.assert_not_called()

    def test_rejects_invalid_or_oversized_rewrites(self):
        for result in [{}, [], {"prompt": ""}, {"prompt": 7}, {"prompt": "x" * 2001}]:
            with self.subTest(result=result):
                self.provider.return_value = StringIO(json.dumps(result))
                self.request_rewrite()
                with self.assertRaises(ValidationError):
                    self.run_draft_task()

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertIn(self.request_rewrite().status_code, (401, 403))
        self.draft_queue.assert_not_called()
