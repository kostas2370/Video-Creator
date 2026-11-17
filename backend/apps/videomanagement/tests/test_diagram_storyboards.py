"""Diagram visuals need structured content, never an unused image prompt."""

import io
import json
import tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from apps.videomanagement.baker_recipes import video
from apps.videomanagement.integrations.llm import get_reply, script_errors
from apps.videomanagement.prompts.storyboard import (
    build_script_prompt,
    build_scene_draft_prompt,
    build_text_storyboard_prompt,
    build_storyboard_revision_prompt,
)
from apps.videomanagement.schemas.drafts import SceneDraftResultSerializer
from apps.videomanagement.serializers.requests import StoryboardSerializer
from apps.videomanagement.services.scenes.narration import ensure_scene_rows
from apps.videomanagement.services.scenes.visuals import create_image_scene
from apps.videomanagement.tests.test_ai_scene_editing import PLAN, storyboard
from apps.videomanagement.utils.storyboard import script_lines, scene_text

DIAGRAM = {
    "template": "steps",
    "title": "Plant growth",
    "items": [
        {"label": "Seed", "detail": ""},
        {"label": "Plant", "detail": ""},
    ],
}


def diagram_script(narration=True):
    script = storyboard({**PLAN, "diagram": deepcopy(DIAGRAM)})
    shot = script["scenes"][0]["sentences"][0]
    shot.pop("image_description")
    if not narration:
        shot.pop("sentence")
    return script


class DiagramStoryboardValidationTests(SimpleTestCase):
    def test_diagrams_accept_omitted_blank_or_legacy_descriptions_and_normalize_review(
        self,
    ):
        for narration in (True, False):
            for description in (None, "", "An unused legacy photo"):
                script = diagram_script(narration)
                shot = script["scenes"][0]["sentences"][0]
                if description is not None:
                    shot["image_description"] = description
                self.assertFalse(
                    script_errors(script, narration=narration, ai_scene_editing=True)
                )
                serializer = StoryboardSerializer(
                    data=script, context={"narration": narration}
                )
                self.assertTrue(serializer.is_valid(), serializer.errors)
                self.assertNotIn(
                    "image_description",
                    serializer.validated_data["scenes"][0]["sentences"][0],
                )
                line = next(script_lines(script))
                self.assertEqual(line.image_description, "")
                self.assertTrue(line.text)

    def test_non_diagrams_still_require_a_description_and_malformed_diagrams_are_rejected(
        self,
    ):
        for editing in (
            {**PLAN, "diagram": None},
            {**PLAN, "diagram": {}},
            {**PLAN, "diagram": {"title": "Invalid"}},
        ):
            script = diagram_script()
            script["scenes"][0]["sentences"][0]["editing"] = editing
            self.assertTrue(script_errors(script, ai_scene_editing=True))
            self.assertFalse(StoryboardSerializer(data=script).is_valid())
        self.assertTrue(script_errors(script, ai_scene_editing=False))

    def test_silent_diagrams_use_existing_diagram_text_without_inventing_a_visual_prompt(
        self,
    ):
        shot = diagram_script(False)["scenes"][0]["sentences"][0]
        self.assertEqual(scene_text(shot), "Plant growth")
        shot["editing"]["diagram"]["title"] = ""
        self.assertEqual(scene_text(shot), "Seed → Plant")

    def test_new_model_results_drop_unused_descriptions_without_a_correction_request(
        self,
    ):
        script = diagram_script()
        script["scenes"][0]["sentences"][0]["image_description"] = "Unused photo"
        with (
            patch(
                "apps.videomanagement.integrations.llm.model_reply",
                return_value=(io.StringIO(json.dumps(script)), "test-model"),
            ) as model,
            patch("apps.videomanagement.integrations.llm.record_llm_trace"),
        ):
            result = get_reply("Plan a diagram", narration=True, ai_scene_editing=True)
        model.assert_called_once()
        self.assertNotIn("image_description", result["scenes"][0]["sentences"][0])

    def test_diagram_prompt_example_validates_in_each_generation_mode(self):
        for mode in ("AI", "WEB"):
            for moving in (True, False):
                for planning in (True, False):
                    for narration in (True, False):
                        prompt = build_script_prompt(
                            image_mode=mode, video=moving, ai_scene_editing=planning,
                            narration=narration,
                        )
                        alternative = prompt.split("Alternative diagram shot example", 1)[1]
                        shot = json.JSONDecoder().raw_decode(alternative[alternative.index("{"):])[0]
                        script = {"title": "Process", "scenes": [{"scene": "Steps", "sentences": [shot]}]}
                        with self.subTest(mode=mode, moving=moving, planning=planning, narration=narration):
                            self.assertNotIn("image_description", shot)
                            self.assertEqual("sentence" in shot, narration)
                            self.assertFalse(script_errors(
                                script, narration=narration, ai_scene_editing=planning,
                                video_provider=moving and mode == "AI",
                            ))
                            serializer = StoryboardSerializer(data=script, context={"narration": narration})
                            self.assertTrue(serializer.is_valid(), serializer.errors)
        prompt = build_text_storyboard_prompt("Keep these exact words.")
        self.assertIn("Alternative diagram shot example", prompt)
        self.assertIn("do not copy these example steps into the story", prompt)

    def test_diagram_only_plan_is_valid_with_editing_disabled(self):
        script = diagram_script()
        shot = script["scenes"][0]["sentences"][0]
        shot["editing"] = {
            "motion_style": "NONE", "motion_intensity": "SUBTLE",
            "transition_after": "CUT", "transition_duration": 0.1,
            "pause_after": 0, "animation_preset": "NONE",
            "animation_accents": False, "overlays": [], "diagram": DIAGRAM,
        }
        for moving in (True, False):
            self.assertFalse(script_errors(script, ai_scene_editing=False, video_provider=moving))
            serializer = StoryboardSerializer(data=script, context={"video_provider": moving})
            self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_diagram_instructions_are_available_without_automatic_effects(self):
        for mode in ("AI", "WEB"):
            for moving in (True, False):
                for narration in (True, False):
                    prompt = build_script_prompt(
                        image_mode=mode, video=moving, narration=narration,
                        ai_scene_editing=False,
                    )
                    self.assertIn("For diagram shots, omit image_description entirely", prompt)
                    self.assertIn("Omit editing on non-diagram shots", prompt)
                    self.assertNotIn("Return editing on every sentences entry", prompt)
        prompts = [
            build_text_storyboard_prompt("A seed grows.", ai_scene_editing=False),
            build_storyboard_revision_prompt(
                diagram_script(), "Explain growth", field_specification="",
                project_context={}, settings={"ai_scene_editing": False},
                image_mode="AI", video_provider=False,
            ),
        ]
        for prompt in prompts:
            self.assertIn("For diagram shots, omit image_description entirely", prompt)
            self.assertIn("Omit editing on non-diagram shots", prompt)

    def test_scene_draft_removes_an_unused_image_description(self):
        for description in (None, "", "Unused photo"):
            data = {"text": "A seed grows into a plant.", "diagram": DIAGRAM}
            if description is not None:
                data["image_description"] = description
            serializer = SceneDraftResultSerializer(data=data)
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertNotIn("image_description", serializer.validated_data)

    def test_generation_import_and_draft_prompts_agree_on_diagram_visuals(self):
        for narration in (True, False):
            for moving in (True, False):
                prompt = build_script_prompt(
                    ai_scene_editing=True,
                    narration=narration,
                    video=moving,
                    image_mode="AI",
                )
                self.assertIn(
                    "For diagram shots, omit image_description entirely", prompt
                )
                if moving:
                    self.assertNotIn("Prefer EXPLAINER for", prompt)
        self.assertIn(
            "For diagram shots, omit image_description entirely",
            build_text_storyboard_prompt("A seed grows.", ai_scene_editing=True),
        )
        self.assertIn(
            "For a diagram, omit image_description entirely",
            build_scene_draft_prompt("Plant growth"),
        )


class DiagramStoryboardGenerationTests(TestCase):
    def test_icon_shortlist_is_available_when_ai_editing_is_disabled(self):
        from apps.videomanagement.services.videos.generation import _planning_options

        project = video.make(mode="AI")
        candidates = [{"id": "test:plant", "name": "Plant", "description": "A plant"}]
        with (
            patch("apps.videomanagement.services.videos.generation.icon_candidates", return_value=candidates) as icons,
            patch("apps.videomanagement.services.videos.generation.ImageProviderRegistry.is_video", return_value=False),
        ):
            options = _planning_options(project, {"message": "Plant growth", "image_mode": "AI", "ai_scene_editing": False})
        icons.assert_called_once_with("Plant growth", user=project.created_by_id)
        self.assertEqual(options["diagram_icons"], candidates)
        prompt = build_script_prompt(**options)
        self.assertIn("test:plant", prompt)

    def test_silent_diagram_without_description_generates_only_a_local_background_and_resumes(
        self,
    ):
        for planning in (True, False):
            with (
                self.subTest(planning=planning),
                tempfile.TemporaryDirectory() as directory,
                override_settings(MEDIA_ROOT=directory),
            ):
                project = video.make(
                    mode="AI",
                    gpt_answer=diagram_script(False),
                    settings={"ai_scene_editing": planning, "narration": False},
                )
                lines, rows = ensure_scene_rows(project)
                row = rows[0]
                self.assertEqual(lines[0].image_description, "")
                self.assertEqual(row.text, "")
                self.assertEqual(row.overlays[0]["diagram"], DIAGRAM)
                with patch(
                    "apps.videomanagement.services.scenes.visuals.ImageProviderRegistry.resolve"
                ) as provider:
                    path = create_image_scene(
                        project,
                        lines[0].image_description,
                        lines[0].text,
                        directory,
                        scene=row,
                        mode="AI",
                    )
                provider.assert_not_called()
                self.assertTrue(Path(path).exists())
                self.assertEqual(row.scene_images.get().prompt, "")
                _, resumed = ensure_scene_rows(project)
                self.assertEqual(resumed[0].pk, row.pk)
