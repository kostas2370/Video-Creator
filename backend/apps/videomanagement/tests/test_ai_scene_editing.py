"""Editing plans use existing scene controls and survive review and retries."""

import io
import json
from copy import deepcopy
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError

from apps.videomanagement.baker_recipes import video
from apps.videomanagement.integrations.llm import get_reply, script_errors
from apps.videomanagement.serializers.requests import StoryboardSerializer
from apps.videomanagement.services.scenes.narration import ensure_scene_rows
from apps.videomanagement.utils.prompt_utils import build_script_prompt

PLAN = {
    "motion_style": "ZOOM_IN", "motion_intensity": "SUBTLE",
    "transition_after": "DISSOLVE", "transition_duration": 0.3, "pause_after": 0.4,
}


def storyboard(plan=PLAN):
    entry = {"sentence": "Cats love boxes.", "image_description": "cat cardboard box"}
    if plan is not None:
        entry["editing"] = deepcopy(plan)
    return {"title": "Cats", "scenes": [{"scene": "Opening", "sentences": [entry]}]}


class SceneEditingPlanTests(SimpleTestCase):
    def test_opt_in_changes_json_shape_and_keeps_video_motion_in_generator(self):
        for mode, provider_video in (("WEB", True), ("AI", False), ("AI", True)):
            with self.subTest(mode=mode, video=provider_video):
                prompt = build_script_prompt(image_mode=mode, video=provider_video, ai_scene_editing=True)
                shape = json.loads(prompt[prompt.index("{"):prompt.rindex("}") + 1])
                self.assertIn("editing", shape["scenes"][0]["sentences"][0])
                self.assertEqual("Use motion_style NONE" in prompt, mode == "AI" and provider_video)
        self.assertNotIn('"editing"', build_script_prompt())

    def test_invalid_or_missing_plan_produces_corrective_errors_only_when_enabled(self):
        self.assertFalse(script_errors(storyboard(), ai_scene_editing=True))
        for changes in ({"motion_style": "SPIN"}, {"pause_after": -1},
                        {"pause_after": 8}, {"pause_after": float("nan")},
                        {"transition_duration": float("inf")}, {"transition_duration": 2}):
            plan = {**PLAN, **changes}
            self.assertTrue(script_errors(storyboard(plan), ai_scene_editing=True))
        self.assertTrue(script_errors(storyboard(None), ai_scene_editing=True))
        self.assertFalse(script_errors(storyboard(None)))

    def test_video_provider_requires_no_editor_motion(self):
        self.assertTrue(script_errors(storyboard(), ai_scene_editing=True, video_provider=True))
        self.assertFalse(script_errors(storyboard({**PLAN, "motion_style": "NONE"}),
                                      ai_scene_editing=True, video_provider=True))

    def test_invalid_plan_is_retried_with_specific_feedback(self):
        invalid = storyboard({**PLAN, "pause_after": 8})
        with patch("apps.videomanagement.integrations.llm.official_gpt_call", side_effect=[
            io.StringIO(json.dumps(invalid)), io.StringIO(json.dumps(storyboard()))
        ]) as call:
            result = get_reply("Make a video", ai_scene_editing=True)
        self.assertEqual(result, storyboard())
        self.assertIn("pause_after", call.call_args.args[0])

    def test_approval_serializer_preserves_and_validates_plans(self):
        serializer = StoryboardSerializer(data=storyboard())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["scenes"][0]["sentences"][0]["editing"], PLAN)
        serializer = StoryboardSerializer(data=storyboard({**PLAN, "motion_style": "SPIN"}))
        self.assertFalse(serializer.is_valid())


class ApplySceneEditingTests(TestCase):
    def test_new_scenes_receive_plans_and_resume_preserves_manual_changes(self):
        vid = video.make(mode="WEB", gpt_answer=storyboard(), settings={"ai_scene_editing": True})
        ensure_scene_rows(vid)
        scene = vid.scenes.get()
        for name, value in PLAN.items():
            self.assertEqual(getattr(scene, name), value)
        scene.motion_style = "PAN_LEFT"
        scene.pause_after = 0
        scene.save()
        ensure_scene_rows(vid)
        scene.refresh_from_db()
        self.assertEqual(scene.motion_style, "PAN_LEFT")
        self.assertEqual(scene.pause_after, 0)
        self.assertEqual(vid.scenes.count(), 1)

    def test_disabled_option_ignores_unrequested_plans(self):
        vid = video.make(mode="WEB", gpt_answer=storyboard(), settings={})
        ensure_scene_rows(vid)
        scene = vid.scenes.get()
        self.assertEqual(scene.motion_style, "NONE")
        self.assertEqual(scene.transition_after, "DEFAULT")
        self.assertEqual(scene.pause_after, 0)

    def test_silent_scripts_also_receive_editing(self):
        script = storyboard()
        del script["scenes"][0]["sentences"][0]["sentence"]
        vid = video.make(mode="WEB", gpt_answer=script, settings={"ai_scene_editing": True, "narration": False})
        ensure_scene_rows(vid)
        self.assertEqual(vid.scenes.get().motion_style, "ZOOM_IN")

    def test_invalid_video_motion_is_not_applied(self):
        vid = video.make(mode="AI", gpt_answer=storyboard(), settings={"ai_scene_editing": True, "provider": "sora"})
        with self.assertRaises(ValidationError):
            ensure_scene_rows(vid)
        self.assertFalse(vid.scenes.exists())
