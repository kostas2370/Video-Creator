"""Shared identity guidance survives edits and reaches each generated visual."""
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.exceptions import ValidationError

from apps.videomanagement.baker_recipes import scene, scene_image, video
from apps.videomanagement.services.scenes import visuals
from apps.videomanagement.serializers.requests import GenerateSerializer, VideoUpdateSerializer
from apps.videomanagement.utils.prompt_utils import build_script_prompt, with_visual_continuity
from apps.videomanagement.tests.api.base import ApiTestCase

BRIEF = "Milo: orange fox, white muzzle, green scarf. Watercolor forest."


class ContinuityPromptTests(SimpleTestCase):
    def test_blank_preserves_existing_prompt(self):
        self.assertEqual(with_visual_continuity("A fox runs", "  "), "A fox runs")

    def test_storyboard_uses_shared_details_only_for_generated_visuals(self):
        for mode in ("AI", "WEB"):
            prompt = build_script_prompt(image_mode=mode, visual_continuity=BRIEF)
            self.assertEqual(BRIEF in prompt, mode == "AI")

    def test_request_limits_and_clearing(self):
        for serializer in (GenerateSerializer, VideoUpdateSerializer):
            field = serializer().fields["visual_continuity"]
            self.assertEqual(field.run_validation(""), "")
            self.assertEqual(field.run_validation(BRIEF), BRIEF)
            with self.assertRaises(ValidationError):
                field.run_validation("x" * 3001)


class ContinuityGenerationTests(TestCase):
    def test_new_and_regenerated_visuals_share_brief_without_changing_saved_prompt(self):
        project = video.make(mode="AI", settings={"visual_continuity": BRIEF})
        line = scene.make(video=project, text="Milo runs.")
        with patch.object(visuals.ImageProviderRegistry, "resolve") as resolve:
            generate = resolve.return_value
            generate.return_value = "media/new.png"
            visuals.create_image_scene(project, "A fox runs", line.text, "media", mode="AI")
            visual = line.scene_images.first()
            self.assertIn(BRIEF, generate.call_args.args[0])
            self.assertEqual(visual.prompt, "A fox runs")
            visuals.generate_new_image(visual, project)
            self.assertEqual(generate.call_args.args[0].count(BRIEF), 1)
            visual.refresh_from_db()
            self.assertEqual(visual.prompt, "A fox runs")

    def test_web_search_does_not_receive_character_instructions(self):
        project = video.make(mode="WEB", settings={"visual_continuity": BRIEF})
        line = scene.make(video=project, text="A fox.")
        visual = scene_image.make(scene=line, prompt="red fox forest")
        with patch.object(visuals.ImageProviderRegistry, "resolve") as resolve:
            resolve.return_value.return_value = "media/new.png"
            visuals.generate_new_image(visual, project)
            self.assertEqual(resolve.return_value.call_args.args[0], "red fox forest")

    def test_new_scene_draft_receives_brief_without_existing_scene_context(self):
        from apps.videomanagement.services.scenes.generation import draft_scene
        project = video.make(mode="AI", settings={"visual_continuity": BRIEF})
        with patch("apps.videomanagement.services.scenes.generation.get_update_sentence",
                   return_value='{"text":"Milo runs.","image_description":"Fox running"}') as draft:
            draft_scene(project, "Next action", use_context=False)
        self.assertIn(BRIEF, draft.call_args.args[0])

    def test_custom_video_provider_receives_shared_brief(self):
        project = video.make(mode="AI", settings={"provider": "custom-video", "visual_continuity": BRIEF})
        visual = scene_image.make(scene=scene.make(video=project), prompt="Milo opens a door")
        with patch.object(visuals.ImageProviderRegistry, "resolve") as resolve:
            resolve.return_value.return_value = "media/new.mp4"
            visuals.generate_new_image(visual, project)
            self.assertIn(BRIEF, resolve.return_value.call_args.args[0])


class ContinuitySettingsTests(ApiTestCase):
    def test_saves_clears_and_preserves_other_settings(self):
        project = self.video_for(settings={"narration": False})
        url = reverse("video-detail", args=[project.pk])
        for value in (BRIEF, ""):
            response = self.client.patch(url, {"visual_continuity": value}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            project.refresh_from_db()
            self.assertEqual(project.settings, {"narration": False, "visual_continuity": value})

    def test_cannot_change_shared_brief_during_generation(self):
        project = self.video_for(status="GENERATION")
        response = self.client.patch(reverse("video-detail", args=[project.pk]), {"visual_continuity": BRIEF}, format="json")
        self.assertEqual(response.status_code, 409)
