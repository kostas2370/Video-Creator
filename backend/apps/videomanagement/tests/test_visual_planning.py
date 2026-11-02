from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from apps.videomanagement.baker_recipes import video
from apps.videomanagement.integrations.llm import script_errors
from apps.videomanagement.serializers.requests import StoryboardSerializer
from apps.videomanagement.services.scenes.narration import ensure_scene_rows
from apps.videomanagement.services.scenes.visual_planning import apply_visual_plans
from apps.videomanagement.tests.test_ai_scene_editing import PLAN, storyboard
from apps.videomanagement.utils.prompt_utils import build_script_prompt, with_shot_plan

LABEL = {"text": "A tiny hiding place", "position": "top-center", "start_fraction": .25, "end_fraction": .75}
EDITING = {**PLAN, "animation_preset": "EXPLAINER", "animation_accents": False, "overlays": [LABEL]}


def visual_storyboard():
    script = storyboard(EDITING)
    script["scenes"][0]["sentences"][0]["shot_plan"] = {
        "role": "HOOK", "visual_focus": "The cat peeking through the box opening",
        "shot_size": "CLOSE_UP", "camera_movement": "PUSH_IN", "target_duration": 8,
    }
    return script


class VisualPlanValidationTests(SimpleTestCase):
    def test_review_preserves_role_animation_and_label_timing(self):
        script = visual_storyboard()
        serializer = StoryboardSerializer(data=script)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["scenes"], script["scenes"])
        self.assertFalse(script_errors(script, ai_scene_editing=True))

    def test_invalid_labels_and_overlapping_emphasis_are_rejected(self):
        for changes in (
            {"text": ""}, {"text": "x" * 81}, {"position": "bottom-center"},
            {"start_fraction": -.1}, {"end_fraction": 1.1},
            {"end_fraction": float("nan")}, {"end_fraction": .25},
        ):
            script = storyboard({**EDITING, "overlays": [{**LABEL, **changes}]})
            self.assertFalse(StoryboardSerializer(data=script).is_valid(), changes)
            self.assertTrue(script_errors(script, ai_scene_editing=True), changes)
        for labels in ([LABEL, LABEL], [LABEL, LABEL, LABEL]):
            self.assertTrue(script_errors(storyboard({**EDITING, "overlays": labels}), ai_scene_editing=True))

    def test_video_providers_allow_labels_but_reject_photo_animation(self):
        script = storyboard({**EDITING, "motion_style": "NONE"})
        self.assertTrue(script_errors(script, ai_scene_editing=True, video_provider=True))
        script["scenes"][0]["sentences"][0]["editing"]["animation_preset"] = "NONE"
        self.assertFalse(script_errors(script, ai_scene_editing=True, video_provider=True))

    def test_planning_instructions_are_opt_in_and_focus_reaches_image_prompts(self):
        for mode in ("AI", "WEB"):
            prompt = build_script_prompt(image_mode=mode, ai_scene_editing=True)
            self.assertIn('"start_fraction"', prompt)
            self.assertIn("avoid repeated framing", prompt)
        self.assertNotIn('"start_fraction"', build_script_prompt())
        self.assertIn("Visual focus: The opening", with_shot_plan("A cat", {"visual_focus": "The opening"}))


class ApplyVisualPlansTests(TestCase):
    def setUp(self):
        self.video = video.make(mode="AI", gpt_answer=visual_storyboard(), settings={"ai_scene_editing": True, "narration": False})
        ensure_scene_rows(self.video)
        self.scene = self.video.scenes.get()

    def test_labels_use_actual_scene_duration_and_remain_editable_on_resume(self):
        self.assertEqual(self.scene.animation_preset, "EXPLAINER")
        self.assertEqual(self.scene.shot_plan["role"], "HOOK")
        self.assertEqual(self.scene.overlays, [])
        apply_visual_plans(self.video)
        self.scene.refresh_from_db()
        self.assertEqual((self.scene.overlays[0]["start"], self.scene.overlays[0]["end"]), (2, 6))
        self.assertEqual(self.scene.overlays[0]["text"], LABEL["text"])
        self.assertTrue(self.scene.shot_plan["overlay_plan"]["applied"])
        # Deleting every planned label is a manual edit too.
        self.scene.overlays = []
        self.scene.animation_preset = "CALM"
        self.scene.save()
        ensure_scene_rows(self.video)
        apply_visual_plans(self.video)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.overlays, [])
        self.assertEqual(self.scene.animation_preset, "CALM")

    def test_existing_user_labels_are_preserved(self):
        self.scene.overlays = [{"text": "My own label"}]
        self.scene.save()
        apply_visual_plans(self.video)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.overlays, [{"text": "My own label"}])
        self.assertTrue(self.scene.shot_plan["overlay_plan"]["applied"])

    def test_missing_narration_defers_timing_until_audio_is_ready(self):
        self.video.settings["narration"] = True
        self.video.save()
        apply_visual_plans(self.video)
        self.scene.refresh_from_db()
        self.assertFalse(self.scene.shot_plan["overlay_plan"]["applied"])
        with patch("apps.videomanagement.services.scenes.visual_planning.stored_file_exists", return_value=True), patch("apps.videomanagement.services.scenes.visual_planning.scene_timing", return_value={"base_duration": 12}):
            apply_visual_plans(self.video)
        self.scene.refresh_from_db()
        self.assertEqual((self.scene.overlays[0]["start"], self.scene.overlays[0]["end"]), (3, 9))

    def test_disabled_planning_does_not_apply_labels(self):
        self.video.settings["ai_scene_editing"] = False
        self.video.save()
        apply_visual_plans(self.video)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.overlays, [])
