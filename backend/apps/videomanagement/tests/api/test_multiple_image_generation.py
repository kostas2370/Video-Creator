import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.videomanagement.baker_recipes import scene
from apps.videomanagement.integrations.llm import script_errors
from apps.videomanagement.models import SceneImage, Video
from apps.videomanagement.services.scenes.visuals import create_image_scenes
from apps.videomanagement.utils.prompt_utils import build_script_prompt
from .base import ApiTestCase


class MultipleImageGenerationTests(ApiTestCase):
    def script(self, additional=None):
        return {
            "title": "Coffee",
            "scenes": [
                {
                    "scene": "Production",
                    "sentences": [
                        {
                            "sentence": "Coffee beans are harvested, roasted, and brewed.",
                            "image_description": "Harvesting coffee beans",
                            "additional_image_descriptions": additional
                            if additional is not None
                            else ["Roasting coffee beans", "Brewing coffee"],
                        }
                    ],
                }
            ],
        }

    def test_prompt_requests_extra_images_under_one_narration_only_when_selected(self):
        default = build_script_prompt(image_mode="AI")
        prompt = build_script_prompt(image_mode="AI", images_per_scene=3)
        silent = build_script_prompt(image_mode="AI", images_per_scene=3, narration=False)
        self.assertIn("Omit narration; images divide the scene duration equally.", silent)
        self.assertNotIn("Keep one narration entry", silent)
        self.assertNotIn("additional_image_descriptions", default)
        self.assertIn("exactly 3 image prompts", prompt)
        self.assertIn("exactly 2 further prompts", prompt)
        self.assertIn("not additional sentences or scenes", prompt)
        self.assertFalse(
            script_errors(self.script(), images_per_scene=3, narration=True)
        )
        for additional in ([], ["One"], ["One", ""], ["One", 42], ["One", "x" * 2001]):
            self.assertTrue(script_errors(self.script(additional), images_per_scene=3))

    @patch("apps.videomanagement.tasks.generate_video_task.delay")
    def test_generation_validates_the_count_and_preserves_it_for_review(self, delay):
        response = self.client.post(
            reverse("generate"),
            {
                "message": "Coffee",
                "image_mode": "AI",
                "provider": "OPENAI",
                "images_per_scene": 3,
                "review_script": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(delay.call_args.kwargs["images_per_scene"], 3)
        video = Video.objects.get(pk=response.data["video"]["id"])
        self.assertEqual(video.settings["generation_params"]["images_per_scene"], 3)
        for options in (
            {"images_per_scene": 0},
            {"images_per_scene": 5},
            {"images_per_scene": 2, "image_mode": "WEB"},
            {"images_per_scene": 2, "image_mode": "AI", "provider": "sora"},
        ):
            self.assertEqual(
                self.client.post(
                    reverse("generate"), {"message": "Coffee", **options}, format="json"
                ).status_code,
                400,
            )

    @patch("apps.videomanagement.tasks.generate_video_task.delay")
    def test_approval_keeps_all_image_prompts_and_rejects_missing_extra_images(
        self, delay
    ):
        video = self.video_for(
            status="REVIEW",
            mode="AI",
            settings={
                "narration": True,
                "generation_params": {
                    "message": "Coffee",
                    "review_script": False,
                    "image_mode": "AI",
                    "provider": "OPENAI",
                    "images_per_scene": 3,
                },
            },
        )
        url = reverse("video-approve-script", args=[video.pk])
        self.assertEqual(
            self.client.post(url, self.script([]), format="json").status_code, 400
        )
        delay.assert_not_called()
        response = self.client.post(url, self.script(), format="json")
        self.assertEqual(response.status_code, 202, response.data)
        video.refresh_from_db()
        self.assertEqual(
            video.gpt_answer["scenes"][0]["sentences"][0][
                "additional_image_descriptions"
            ],
            ["Roasting coffee beans", "Brewing coffee"],
        )
        self.assertEqual(delay.call_args.kwargs["images_per_scene"], 3)

    def test_generation_and_resume_create_ordered_images_without_duplicating_narration_or_paid_images(
        self,
    ):
        with (
            tempfile.TemporaryDirectory() as directory,
            override_settings(MEDIA_ROOT=directory),
        ):
            Image.new("RGB", (32, 32), "red").save(Path(directory, "red.png"))
            video = self.video_for(
                mode="AI",
                gpt_answer=self.script(),
                settings={
                    "narration": True,
                    "images_per_scene": 3,
                    "visual_continuity": "Warm documentary style",
                },
            )
            sentence = self.script()["scenes"][0]["sentences"][0]
            row = scene.make(
                video=video,
                text=sentence["sentence"],
                is_last=False,
                shot_plan={"subject_action": "Harvesting coffee"},
            )
            with patch(
                "apps.videomanagement.services.scenes.visuals.ImageProviderRegistry.resolve"
            ) as resolve:
                provider = resolve.return_value
                provider.side_effect = [
                    "red.png",
                    RuntimeError("temporary provider error"),
                    "red.png",
                ]
                create_image_scenes(video, mode="AI", provider="OPENAI")
                self.assertEqual(video.scenes.count(), 1)
                shots = list(row.scene_images.all())
                self.assertEqual([shot.position for shot in shots], [0, 1, 2])
                self.assertEqual(
                    [shot.prompt for shot in shots],
                    [
                        sentence["image_description"],
                        *sentence["additional_image_descriptions"],
                    ],
                )
                self.assertFalse(shots[1].file)
                self.assertNotIn(
                    "Harvesting coffee", provider.call_args_list[2].args[0]
                )
                self.assertIn(
                    "Warm documentary style", provider.call_args_list[2].args[0]
                )
                ids = [shot.pk for shot in shots]
                provider.reset_mock()
                provider.side_effect = None
                provider.return_value = "red.png"
                create_image_scenes(video, mode="AI", provider="OPENAI")
                provider.assert_called_once()
                self.assertEqual(
                    list(row.scene_images.values_list("pk", flat=True)), ids
                )
                self.assertEqual(SceneImage.objects.filter(scene=row).count(), 3)
                provider.reset_mock()
                create_image_scenes(video, mode="AI", provider="OPENAI")
                provider.assert_not_called()
