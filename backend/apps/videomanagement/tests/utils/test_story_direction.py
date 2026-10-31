"""Story direction applies to scripts, editor drafts and actual provider requests."""
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.videomanagement.integrations.visuals.video_http import shot_prompt
from apps.videomanagement.utils.prompt_utils import build_script_prompt, build_scene_draft_prompt
from apps.videomanagement.utils.transitions import default_transition, intro_transition, scene_transition


class StoryDirectionTests(SimpleTestCase):
    def test_video_scripts_and_editor_drafts_share_connected_story_direction(self):
        prompts = [
            build_script_prompt(image_mode="AI", video=True, narration=False, scene_count=4),
            build_scene_draft_prompt("Continue the breakfast scene", video=True, scenario={"location": "cafe"}),
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt[:60]):
                self.assertIn("one protagonist's understandable emotional sequence", prompt)
                self.assertIn("state and ownership", prompt)
                self.assertIn("character positions, eyelines", prompt)
                self.assertIn("instead of giving every shot the same length", prompt)
                self.assertIn("For factual or instructional requests", prompt)
                self.assertIn("No montage, internal cuts, fade to black", prompt)
        self.assertIn("exactly 4 scenes", prompts[0])
        self.assertIn("do not restart its setup", prompts[1])
        self.assertIn('"location": "cafe"', prompts[1])

    def test_web_and_still_scripts_do_not_receive_video_story_constraints(self):
        for mode in ("WEB", "AI"):
            prompt = build_script_prompt(image_mode=mode, video=False)
            self.assertNotIn("one protagonist's understandable emotional sequence", prompt)
            self.assertNotIn("No background music", prompt)

    def test_provider_prompt_keeps_explicit_dialogue_and_suppresses_scores_and_fades(self):
        prompt = shot_prompt('Bananito says "Breakfast is ready".', "3D animation", "frame.png")
        self.assertIn('Bananito says "Breakfast is ready".', prompt)
        self.assertIn("explicitly specified dialogue", prompt)
        self.assertIn("No background music or invented speech", prompt)
        self.assertIn("opening fade, or closing transition", prompt)
        self.assertIn("preserve subjects, clothing, lighting", prompt)

    def test_series_cut_defaults_preserve_explicit_scene_video_and_intro_choices(self):
        settings = {"creation_mode": "SERIES"}
        scene = SimpleNamespace(transition_after="DEFAULT", transition_duration=None)
        self.assertEqual(scene_transition(scene, settings), ("CUT", None))
        self.assertEqual(intro_transition(settings), ("CUT", None))
        self.assertEqual(default_transition({}), "FADE")
        settings.update(transition_default="FADE", transition_duration=0.3)
        self.assertEqual(scene_transition(scene, settings), ("FADE", 0.3))
        scene.transition_after = "DISSOLVE"
        scene.transition_duration = 0.2
        self.assertEqual(scene_transition(scene, settings), ("DISSOLVE", 0.2))
        settings.update(intro_transition="CUT")
        self.assertEqual(intro_transition(settings), ("CUT", 0.3))
