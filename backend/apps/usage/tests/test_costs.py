from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import video, scene
from apps.usage.estimates import media_estimate
from apps.usage.models import AIUsage, GenerationEstimate
from apps.usage.services import record_usage, video_usage, current_video


@override_settings(IMAGE_MODEL="gpt-image-2", IMAGE_QUALITY="high", AI_COST_RATES={})
class GenerationCostTests(TestCase):
    def test_economy_estimates_medium_images_without_changing_standard_or_voice_costs(self):
        standard = media_estimate(self.project, self.storyboard)
        economy = media_estimate(self.project, {**self.storyboard, "generation_mode": "ECONOMY"})
        standard_image = next(line for line in standard["lines"] if line["service"] == "images")
        economy_image = next(line for line in economy["lines"] if line["service"] == "images")
        self.assertEqual(standard_image["low_usd"], "0.16500000")
        self.assertEqual(economy_image["low_usd"], "0.04100000")
        self.assertEqual(standard["lines"][0], economy["lines"][0])
        self.assertNotIn("generation_mode", self.project.settings)

    def setUp(self):
        self.owner = user.make(use_service_api_keys=True)
        self.project = video.make(
            created_by=self.owner,
            mode="AI",
            settings={"narration": True, "provider": "OPENAI"},
        )
        self.storyboard = {
            "title": "A story",
            "scenes": [
                {
                    "scene": "Opening",
                    "sentences": [{"sentence": "Hello", "image_description": "A fox"}],
                }
            ],
        }
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def estimate(self, **data):
        return self.client.post(
            reverse("ai_cost_estimate"),
            {"video_id": str(self.project.pk), **data},
            format="json",
        )

    def test_estimate_uses_edited_script_without_saving_or_calling_providers(self):
        with patch(
            "apps.videomanagement.integrations.visuals.openai_images.OpenAI"
        ) as provider:
            result = self.estimate(storyboard=self.storyboard)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["low_usd"], "0.16507500")
        self.assertEqual(result.data["high_usd"], "0.21107500")
        self.assertTrue(result.data["partial"])
        provider.assert_not_called()
        self.assertFalse(GenerationEstimate.objects.exists())
        self.assertFalse(AIUsage.objects.exists())
        self.project.refresh_from_db()
        self.assertNotEqual(self.project.gpt_answer, self.storyboard)
        self.storyboard["scenes"][0]["sentences"][0]["sentence"] *= 2
        self.assertEqual(
            self.estimate(storyboard=self.storyboard).data["low_usd"], "0.16515000"
        )

    def test_silent_character_video_separates_image_preparation_and_later_animation(
        self,
    ):
        self.project.settings = {
            "narration": False,
            "provider": "runway",
            "character_references": True,
        }
        self.storyboard["scenes"][0]["sentences"][0].update(
            sentence="", shot_plan={"target_duration": 6.2}
        )
        self.project.save()
        estimate = self.estimate(storyboard=self.storyboard).data
        self.assertEqual(
            [row["service"] for row in estimate["lines"]], ["video", "images", "text"]
        )
        self.assertEqual(estimate["lines"][0]["units"]["seconds"], 7)
        self.assertIn("later", estimate["lines"][0]["note"])
        shot = scene.make(video=self.project, shot_plan={"target_duration": 6.2})
        visual = self.estimate(scene_id=str(shot.pk), operation="visual").data
        animation = self.estimate(scene_id=str(shot.pk), operation="animation").data
        self.assertEqual([row["service"] for row in visual["lines"]], ["images"])
        self.assertEqual(animation["low_usd"], "0.84000000")

    def test_unknown_voice_is_excluded_from_partial_subtotal(self):
        self.project.voice_model.provider = "ELEVENLABS"
        self.project.voice_model.save()
        result = self.estimate(storyboard=self.storyboard).data
        self.assertTrue(result["partial"])
        self.assertIsNone(result["lines"][0]["low_usd"])
        self.assertEqual(result["low_usd"], "0.16500000")

    @override_settings(IMAGE_MODEL="unpriced-model")
    def test_all_unknown_prices_are_null_and_never_free(self):
        self.project.settings["narration"] = False
        result = media_estimate(self.project, self.storyboard)
        self.assertIsNone(result["low_usd"])
        self.assertTrue(result["partial"])

    def test_disabled_narration_and_web_media_have_no_paid_generation(self):
        self.project.mode = "WEB"
        self.project.settings = {"narration": False}
        result = media_estimate(self.project, self.storyboard)
        self.assertEqual(result["low_usd"], "0.00000000")
        self.assertFalse(result["partial"])

    def test_estimates_and_project_comparisons_are_private_and_validate_inputs(self):
        other = video.make(created_by=user.make())
        shot = scene.make(video=other)
        self.assertEqual(self.estimate(video_id=str(other.pk)).status_code, 404)
        self.assertEqual(self.estimate(scene_id=str(shot.pk)).status_code, 404)
        self.assertEqual(
            self.client.get(reverse("ai_project_cost", args=[other.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.estimate(storyboard={"scenes": "invalid"}).status_code, 400
        )
        self.assertEqual(self.estimate(operation="bad").status_code, 400)
        self.client.force_authenticate(None)
        self.assertIn(self.estimate(storyboard=self.storyboard).status_code, (401, 403))

    def test_recorded_cost_keeps_rate_snapshot_and_marks_partial_coverage(self):
        with video_usage(self.project):
            record_usage(self.owner, "tts", "OPENAI", "tts-1", characters=1000)
            record_usage(self.owner, "tts", "unknown", characters=20, custom=True)
        row = AIUsage.objects.get(provider="OPENAI")
        self.assertEqual(row.cost_usd, Decimal("0.015"))
        self.assertEqual(row.video_id, self.project.pk)
        self.assertEqual(row.cost_details["characters"], "0.000015")
        with override_settings(
            AI_COST_RATES={"tts:OPENAI:tts-1": {"characters": "10"}}
        ):
            result = self.client.get(
                reverse("ai_project_cost", args=[self.project.pk])
            ).data
        self.assertEqual(result["recorded"]["totals"]["cost_usd"], "0.01500000")
        self.assertEqual(result["recorded"]["totals"]["requests_with_cost"], 1)
        self.assertEqual(result["recorded"]["totals"]["requests"], 2)
        self.assertIsNone(result["estimate"])
        self.assertIsNone(current_video.get())

    def test_usage_context_is_reset_after_failure_and_rejects_wrong_owner(self):
        with self.assertRaises(RuntimeError):
            with video_usage(self.project):
                raise RuntimeError()
        self.assertIsNone(current_video.get())
        with video_usage(self.project):
            record_usage(user.make(), "tts", "OPENAI", "tts-1", characters=10)
        self.assertIsNone(AIUsage.objects.get().video_id)

    def test_image_cost_requires_separate_text_and_image_input_measurements(self):
        record_usage(
            self.owner,
            "images",
            "OPENAI",
            "gpt-image-2",
            {"input_tokens": 30, "output_tokens": 100},
            images=1,
        )
        self.assertIsNone(AIUsage.objects.get().cost_usd)
        record_usage(
            self.owner,
            "images",
            "OPENAI",
            "gpt-image-2",
            {
                "input_tokens": 30,
                "input_tokens_details": {"text_tokens": 10, "image_tokens": 20},
                "output_tokens": 100,
            },
            images=1,
        )
        self.assertEqual(AIUsage.objects.latest("pk").cost_usd, Decimal("0.003210"))

    def test_custom_provider_name_cannot_inherit_builtin_pricing(self):
        record_usage(self.owner, "tts", "OPENAI", "tts-1", characters=100, custom=True)
        self.assertIsNone(AIUsage.objects.get().cost_usd)

    @override_settings(
        AI_COST_RATES={
            "images:custom:": {
                "images": "0.2",
                "source": "https://example.test/pricing",
                "checked_at": "2026-10-01",
            }
        }
    )
    def test_configured_rates_support_custom_provider_estimates_and_recording(self):
        self.project.settings = {"narration": False, "provider": "custom"}
        result = media_estimate(self.project, self.storyboard)
        self.assertEqual(result["low_usd"], "0.20000000")
        record_usage(self.owner, "images", "custom", images=2, custom=True)
        self.assertEqual(AIUsage.objects.get().cost_usd, Decimal("0.4"))

    @override_settings(AI_COST_RATES={"tts:OPENAI:tts-1": {"characters": "NaN"}})
    def test_invalid_rate_does_not_interrupt_usage_recording(self):
        record_usage(self.owner, "tts", "OPENAI", "tts-1", characters=100)
        self.assertIsNone(AIUsage.objects.get().cost_usd)

    def test_saved_estimate_is_available_beside_recorded_usage(self):
        estimate = media_estimate(self.project, self.storyboard)
        GenerationEstimate.objects.create(video=self.project, estimate=estimate)
        response = self.client.get(reverse("ai_project_cost", args=[self.project.pk]))
        self.assertEqual(response.data["estimate"]["low_usd"], estimate["low_usd"])
        self.assertTrue(response.data["estimate"]["partial"])
        self.assertEqual(response.data["recorded"]["totals"]["cost_usd"], "0.00000000")

    def test_approval_saves_reviewed_estimate_and_resume_preserves_it(self):
        from apps.videomanagement.services.videos.jobs import approve_script
        from apps.videomanagement.services.videos.generation import (
            generate_scene_assets,
        )

        self.project.status = "REVIEW"
        self.project.settings["generation_params"] = {
            "image_mode": "AI",
            "narration": True,
            "provider": "OPENAI",
        }
        self.project.save()
        with patch("apps.videomanagement.services.videos.jobs.dispatch_video_job"):
            approve_script(self.project, self.storyboard)
        saved = GenerationEstimate.objects.get(video=self.project).estimate
        self.assertEqual(saved["low_usd"], "0.16507500")
        self.project.gpt_answer = self.storyboard
        self.project.settings["narration"] = False
        with patch(
            "apps.videomanagement.services.videos.generation.make_scenes_speech"
        ):
            generate_scene_assets(self.project)
        self.assertEqual(
            GenerationEstimate.objects.get(video=self.project).estimate, saved
        )

    def test_scenario_estimate_is_available_before_a_project_exists_without_ai_calls(
        self,
    ):
        with patch("apps.videomanagement.integrations.llm.OpenAI") as provider:
            response = self.client.post(
                reverse("ai_scenario_estimate"),
                {
                    "message": "A fox finds a lantern",
                    "gpt_model": "gpt-5.4-mini",
                    "scene_count": 8,
                },
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scope"], "scenario")
        self.assertGreater(Decimal(response.data["low_usd"]), 0)
        self.assertGreater(
            Decimal(response.data["high_usd"]), Decimal(response.data["low_usd"])
        )
        self.assertEqual(response.data["lines"][0]["model"], "gpt-5.4-mini")
        self.assertFalse(AIUsage.objects.exists())
        provider.assert_not_called()

    def test_scenario_endpoint_rejects_invalid_inputs_and_requires_authentication(self):
        endpoint = reverse("ai_scenario_estimate")
        for payload in ({"message": ""}, {"message": "fox", "scene_count": 61}):
            self.assertEqual(
                self.client.post(endpoint, payload, format="json").status_code, 400
            )
        self.client.force_authenticate(None)
        self.assertIn(
            self.client.post(endpoint, {"message": "fox"}, format="json").status_code,
            (401, 403),
        )

    def test_recorded_scenario_is_included_in_generation_estimate_and_project_total_once(
        self,
    ):
        with video_usage(self.project):
            record_usage(
                self.owner,
                "text",
                "OPENAI",
                "gpt-5.4-mini",
                {"input_tokens": 1000, "output_tokens": 2000},
            )
        result = self.estimate(storyboard=self.storyboard).data
        self.assertEqual(result["low_usd"], "0.17482500")
        self.assertFalse(result["partial"])
        self.assertIn("already drafted", result["lines"][-1]["label"])
        response = self.client.get(
            reverse("ai_project_cost", args=[self.project.pk])
        ).data
        self.assertEqual(response["recorded"]["totals"]["cost_usd"], "0.00975000")
        self.assertEqual(response["scenario"]["low_usd"], "0.00975000")

    def test_scenario_requests_with_unknown_prices_keep_the_total_partial(self):
        with video_usage(self.project):
            record_usage(
                self.owner,
                "text",
                "OPENAI",
                "gpt-5.4-mini",
                {"input_tokens": 1000, "output_tokens": 2000},
            )
            record_usage(
                self.owner,
                "text",
                "GEMINI",
                "unknown",
                {"input_tokens": 1000, "output_tokens": 2000},
            )
        result = self.estimate(storyboard=self.storyboard).data
        self.assertTrue(result["partial"])
        self.assertIn("1 of 2", result["lines"][-1]["note"])

    def test_drafting_links_usage_to_the_project_before_returning_storyboard_review(
        self,
    ):
        from apps.videomanagement.services.videos.generation import generate_video

        def draft(*args, **kwargs):
            self.assertEqual(current_video.get().pk, self.project.pk)
            record_usage(
                self.owner,
                "text",
                "OPENAI",
                "gpt-5.4-mini",
                {"input_tokens": 1000, "output_tokens": 2000},
            )
            return self.storyboard

        self.project.gpt_answer = None
        with (
            patch(
                "apps.videomanagement.services.videos.generation.get_reply",
                side_effect=draft,
            ),
            patch(
                "apps.videomanagement.services.videos.generation.generate_directory",
                return_value="/tmp/scenario-test",
            ),
            patch(
                "apps.videomanagement.services.videos.generation.available_voice",
                return_value=self.project.voice_model,
            ),
        ):
            generate_video(
                self.project,
                message="fox",
                gpt_model="gpt-5.4-mini",
                image_mode="AI",
                avatar_selection=None,
                style="natural",
                target_audience="",
                voice_id=str(self.project.voice_model_id),
                review_script=True,
            )
        self.assertEqual(AIUsage.objects.get().video_id, self.project.pk)
        self.assertIsNone(current_video.get())
