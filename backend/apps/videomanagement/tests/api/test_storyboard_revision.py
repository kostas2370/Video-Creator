import json
from copy import deepcopy
from io import StringIO
from unittest.mock import patch

from django.urls import reverse
from rest_framework.exceptions import ValidationError

from apps.usermanagement.baker_recipes import user
from apps.videomanagement import draft_tasks
from apps.usage.services import current_video

from .base import ApiTestCase


class StoryboardRevisionTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.storyboard = {
            "title": "Original",
            "visual_continuity": "",
            "generation_mode": "ECONOMY",
            "scenes": [
                {
                    "scene": "Opening",
                    "sentences": [
                        {
                            "sentence": "Original narration",
                            "image_description": "An empty street",
                        }
                    ],
                }
            ],
        }
        self.video = self.video_for(
            status="REVIEW",
            gpt_answer=self.storyboard,
            settings={
                "gpt_model": "claude-selected",
                "narration": True,
                "generation_params": {
                    "scene_count": 1,
                    "message": "An empty street",
                    "review_script": False,
                },
            },
        )
        self.url = reverse("video-revise-storyboard", args=[self.video.pk])
        self.proposal = {**deepcopy(self.storyboard), "title": "Revised"}
        provider = patch(
            "apps.videomanagement.services.videos.storyboard_revision.get_reply",
            return_value=StringIO(json.dumps(self.proposal)),
        )
        self.provider = provider.start()
        self.addCleanup(provider.stop)

    def request_revision(self, **changes):
        return self.client.post(
            self.url,
            {
                "instructions": "Make it suspenseful",
                "storyboard": self.storyboard,
                **changes,
            },
            format="json",
        )

    def test_returns_validated_preview_without_changing_saved_storyboard_or_generating_media(
        self,
    ):
        response = self.request_revision()
        self.assertEqual(response.status_code, 202, response.data)
        self.assertIs(
            self.draft_queue.call_args.args[0], draft_tasks.revise_storyboard_task
        )
        self.provider.assert_not_called()
        result = self.run_draft_task()
        self.assertEqual(result, self.proposal)
        self.video.refresh_from_db()
        self.assertEqual(self.video.gpt_answer, self.storyboard)
        self.assertEqual(self.video.status, "REVIEW")
        self.assertFalse(self.video.scenes.exists())
        self.assertEqual(self.provider.call_args.kwargs["gpt_model"], "claude-selected")
        self.assertIn("Make it suspenseful", self.provider.call_args.args[0])
        self.assertIsNone(current_video.get())

    def test_invalid_input_and_non_review_projects_do_not_queue(self):
        for changes in [
            {"instructions": " "},
            {"instructions": "x" * 2001},
            {"storyboard": {}},
        ]:
            self.assertEqual(self.request_revision(**changes).status_code, 400)
        self.video.status = "READY"
        self.video.save()
        self.assertEqual(self.request_revision().status_code, 400)
        self.draft_queue.assert_not_called()

    def test_enforces_owner_and_rechecks_status_in_worker(self):
        self.client.force_authenticate(user.make())
        self.assertEqual(self.request_revision().status_code, 404)
        self.client.force_authenticate(self.user)
        self.request_revision()
        self.video.status = "READY"
        self.video.save()
        with self.assertRaises(ValidationError):
            self.run_draft_task()
        self.provider.assert_not_called()

    def test_rejects_malformed_ai_output_and_missing_narration(self):
        missing_narration = deepcopy(self.proposal)
        missing_narration["scenes"][0]["sentences"][0]["sentence"] = ""
        for result in [
            "not json",
            {},
            {**self.proposal, "scenes": []},
            missing_narration,
        ]:
            with self.subTest(result=result):
                self.provider.return_value = StringIO(json.dumps(result))
                self.request_revision()
                with self.assertRaises(ValidationError):
                    self.run_draft_task()

    def test_non_narrated_revision_and_render_mode_preservation(self):
        self.video.settings["narration"] = False
        self.video.save()
        self.proposal["generation_mode"] = "STANDARD"
        self.proposal["scenes"][0]["sentences"][0].pop("sentence")
        self.provider.return_value = StringIO(json.dumps(self.proposal))
        self.request_revision()
        result = self.run_draft_task()
        self.assertEqual(result["generation_mode"], "ECONOMY")
        self.assertNotIn("sentence", result["scenes"][0]["sentences"][0])

    @patch("apps.videomanagement.tasks.generate_video_task.delay")
    def test_approval_uses_revised_scene_count(self, generate):
        revised = deepcopy(self.proposal)
        revised["scenes"] *= 2
        response = self.client.post(
            reverse("video-approve-script", args=[self.video.pk]),
            revised,
            format="json",
        )
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(generate.call_args.kwargs["scene_count"], 2)

    def test_empty_optional_diagram_is_normalized_without_another_paid_request(self):
        from ..test_ai_scene_editing import PLAN

        self.video.settings["ai_scene_editing"] = True
        self.video.save()
        self.proposal["scenes"][0]["sentences"][0]["editing"] = {**PLAN, "diagram": {}}
        self.provider.return_value = StringIO(json.dumps(self.proposal))
        self.request_revision()
        result = self.run_draft_task()
        self.assertIsNone(result["scenes"][0]["sentences"][0]["editing"]["diagram"])
        self.provider.assert_called_once()
        self.video.refresh_from_db()
        self.assertEqual(self.video.gpt_answer, self.storyboard)

    def test_incomplete_nonempty_diagram_is_still_rejected(self):
        from ..test_ai_scene_editing import PLAN

        self.proposal["scenes"][0]["sentences"][0]["editing"] = {
            **PLAN,
            "diagram": {"title": "Incomplete"},
        }
        self.provider.return_value = StringIO(json.dumps(self.proposal))
        self.request_revision()
        with self.assertRaises(ValidationError):
            self.run_draft_task()
