from unittest.mock import patch

from django.urls import reverse

from apps.videomanagement.integrations.llm import script_errors
from apps.videomanagement.serializers.requests import StoryboardSerializer
from apps.videomanagement.services.scenes.narration import make_scenes_speech
from apps.videomanagement.utils.prompt_utils import build_script_prompt, script_lines
from .base import ApiTestCase


class SceneStoryboardTests(ApiTestCase):
    narration = "A seed lands in the soil. Rain helps it take root. Soon a green shoot reaches toward the light."

    def script(self):
        return {
            "title": "Growing",
            "scenes": [
                {
                    "scene": "A new beginning",
                    "narration": self.narration,
                    "image_description": "A green seedling in moist soil",
                }
            ],
        }

    def test_prompts_request_scene_paragraphs_and_a_flat_storyboard(self):
        import json

        prompt = build_script_prompt(scene_count=3)
        shape = json.loads(prompt[prompt.index("{") : prompt.rindex("}") + 1])
        self.assertIn("narration", shape["scenes"][0])
        self.assertNotIn("sentences", shape["scenes"][0])
        self.assertIn("not one sentence", prompt)
        self.assertIn("usually 1–4 connected sentences", prompt)
        self.assertNotIn("never a paragraph", prompt)

    def test_model_validation_and_approval_accept_a_whole_paragraph(self):
        script = self.script()
        self.assertEqual(script_errors(script, narration=True, scene_count=1), [])
        serializer = StoryboardSerializer(data=script)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["scenes"][0]["narration"], self.narration
        )
        for changes in (
            {"narration": ""},
            {"narration": "x" * 2001},
            {"narration": []},
            {"sentences": [{"sentence": "Other", "image_description": "Other"}]},
        ):
            changed = {**script, "scenes": [{**script["scenes"][0], **changes}]}
            self.assertTrue(script_errors(changed, narration=True))
            self.assertFalse(StoryboardSerializer(data=changed).is_valid())

    def test_legacy_scene_entries_keep_their_existing_boundaries(self):
        script = {
            "title": "Old",
            "scenes": [
                {
                    "scene": "Opening",
                    "sentences": [
                        {"sentence": "First line.", "image_description": "First image"},
                        {
                            "sentence": "Second line.",
                            "image_description": "Second image",
                        },
                    ],
                }
            ],
        }
        self.assertEqual(
            [(line.text, line.is_last) for line in script_lines(script)],
            [("First line.", False), ("Second line.", True)],
        )
        self.assertTrue(StoryboardSerializer(data=script).is_valid())

    def test_several_sentences_create_one_scene_and_one_narration_request(self):
        video = self.video_for(
            mode="AI", gpt_answer=self.script(), settings={"narration": True}
        )
        with patch(
            "apps.videomanagement.services.scenes.narration.narrate_scene"
        ) as speak:
            make_scenes_speech(video)
        speak.assert_called_once()
        self.assertEqual(video.scenes.count(), 1)
        self.assertEqual(video.scenes.get().text, self.narration)
        self.assertEqual(speak.call_args.args[0].text, self.narration)

    @patch("apps.videomanagement.tasks.generate_video_task.delay")
    def test_review_saves_flat_scene_narration_and_queues_it_unchanged(self, delay):
        video = self.video_for(
            mode="AI",
            status="REVIEW",
            settings={
                "narration": True,
                "generation_params": {"message": "Growing", "review_script": False},
            },
        )
        response = self.client.post(
            reverse("video-approve-script", args=[video.pk]),
            self.script(),
            format="json",
        )
        self.assertEqual(response.status_code, 202, response.data)
        video.refresh_from_db()
        self.assertEqual(video.gpt_answer, self.script())
        delay.assert_called_once()

    def test_scene_drafts_accept_paragraphs_and_the_scene_count_option(self):
        import json

        video = self.video_for(status="READY")
        paragraphs = [
            {"text": self.narration * 4, "image_description": "A seedling"}
        ] * 3
        with patch(
            "apps.videomanagement.services.scenes.generation.get_update_sentence",
            return_value=json.dumps({"scenes": paragraphs}),
        ) as draft:
            response = self.client.post(
                reverse("video-draft-scene", args=[video.pk]),
                {
                    "prompt": "A plant growing",
                    "draft_type": "section",
                    "scene_count": 3,
                },
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["scenes"], paragraphs)
        self.assertIn("exactly 3 scenes", draft.call_args.args[0])
        self.assertNotIn("ONE concise sentence", draft.call_args.args[0])
