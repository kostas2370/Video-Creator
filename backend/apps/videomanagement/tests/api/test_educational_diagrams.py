import tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

from apps.usage.estimates import media_estimate
from apps.videomanagement.serializers.requests import StoryboardSerializer
from apps.videomanagement.services.scenes.narration import ensure_scene_rows
from apps.videomanagement.services.scenes.visuals import create_image_scene, scene_reference
from apps.videomanagement.services.scenes.visual_planning import apply_visual_plans
from apps.videomanagement.tests.test_ai_scene_editing import PLAN, storyboard
from apps.videomanagement.baker_recipes import scene

from .base import ApiTestCase

DIAGRAM = {"template": "steps", "title": "How it works", "items": [
    {"label": "Start", "detail": "The first stage"}, {"label": "Finish", "detail": "The result"},
]}


class EducationalDiagramTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)

    def test_ai_plan_creates_editable_diagram_without_paid_visuals(self):
        script = storyboard({**PLAN, "diagram": DIAGRAM, "overlays": []})
        serializer = StoryboardSerializer(data=script)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        video = self.video_for(mode="AI", status="READY", gpt_answer=script,
                               settings={"ai_scene_editing": True, "narration": False})
        _, rows = ensure_scene_rows(video)
        row = rows[0]
        self.assertEqual(row.overlays[0]["diagram"], DIAGRAM)
        with patch("apps.videomanagement.services.scenes.visuals.ImageProviderRegistry.resolve") as provider:
            path = create_image_scene(video, "An explanation", row.text, self.directory, scene=row, mode="AI", provider="runway")
        provider.assert_not_called()
        self.assertTrue(Path(path).exists())
        self.assertFalse(row.scene_images.get().with_audio)
        self.assertIsNone(scene_reference(row, video, "OPENAI"))
        with patch("apps.usage.estimates.ImageProviderRegistry.provider") as calculator:
            estimate = media_estimate(video)
        calculator.assert_not_called()
        self.assertEqual(estimate["lines"], [])
        # Deleting the diagram is a manual edit and must survive a resume.
        row.overlays = []
        row.save(update_fields=["overlays"])
        ensure_scene_rows(video)
        apply_visual_plans(video)
        row.refresh_from_db()
        self.assertEqual(row.overlays, [])

    def test_editor_save_preview_clear_and_lock(self):
        video = self.video_for(status="READY")
        row = scene.make(video=video)
        url = reverse("scene-overlays", args=[row.pk])
        response = self.client.patch(url, {"overlays": [{"kind": "diagram", "diagram": DIAGRAM}]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        preview = self.client.get(reverse("video-preview", args=[video.pk]))
        self.assertEqual(preview.data["segments"][0]["overlays"][0]["diagram"], DIAGRAM)
        self.scene_queue.assert_not_called()
        video.status = "RENDERING"
        video.save()
        self.assertEqual(self.client.patch(url, {"overlays": []}, format="json").status_code, 409)
        video.status = "READY"
        video.save()
        self.assertEqual(self.client.patch(url, {"overlays": []}, format="json").status_code, 200)

    def test_planner_rejects_extra_labels_on_a_diagram(self):
        script = storyboard({**PLAN, "diagram": DIAGRAM, "overlays": [
            {"text": "Clutter", "start_fraction": 0, "end_fraction": 1},
        ]})
        self.assertFalse(StoryboardSerializer(data=script).is_valid())

    def test_mixed_project_still_estimates_all_narration_but_only_paid_visuals(self):
        script = storyboard({**PLAN, "diagram": DIAGRAM})
        ordinary = deepcopy(script["scenes"][0]["sentences"][0])
        ordinary["editing"].pop("diagram")
        script["scenes"][0]["sentences"].append(ordinary)
        video = self.video_for(mode="AI", gpt_answer=script, settings={"ai_scene_editing": True, "narration": True})
        from apps.videomanagement.integrations.visuals.openai_images import OpenAIImageProvider
        with patch.object(OpenAIImageProvider, "calculate", wraps=OpenAIImageProvider.calculate) as calculator:
            estimate = media_estimate(video)
        self.assertEqual(calculator.call_args.args[0].count, 1)
        narration = next(line for line in estimate["lines"] if line["service"] == "tts")
        self.assertEqual(narration["units"]["requests"], 2)
