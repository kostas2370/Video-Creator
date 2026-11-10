import json
from io import StringIO
from unittest.mock import patch
from uuid import uuid4

from django.test import override_settings
from django.urls import reverse
from model_bakery import baker
from PIL import Image
from rest_framework.exceptions import ValidationError

from apps.usermanagement.baker_recipes import user
from apps.usage.services import current_video
from apps.videomanagement import draft_tasks
from apps.videomanagement.serializers.models import SceneSerializer
from apps.videomanagement.services.scenes.starting_frame_review import (
    review_comparison_sheet,
    review_source_key,
    review_starting_frame,
)

from . import test_starting_frames


class StartingFrameReviewTests(test_starting_frames.StartingFrameTests):
    def setUp(self):
        super().setUp()
        self.review_url = reverse("scene-review-starting-frame", args=[self.scene.pk])
        self.review = {
            "verdict": "needs_changes",
            "summary": "The scarf color differs from the reference.",
            "findings": [
                {
                    "category": "character",
                    "issue": "Milo has a red scarf.",
                    "fix": "Use the green scarf in the reference.",
                }
            ],
            "suggested_description": "Milo at the forest gate wearing his green scarf.",
        }
        provider = patch(
            "apps.videomanagement.services.scenes.starting_frame_review.get_reply",
            return_value=StringIO(json.dumps(self.review)),
        )
        self.provider = provider.start()
        self.addCleanup(provider.stop)

    def request_review(self, **extra):
        return self.client.post(
            self.review_url,
            {
                "asset_id": str(self.scene.starting_asset_id),
                **extra,
            },
            format="json",
        )

    def test_review_is_queued_without_calling_provider_or_changing_approval(self):
        response = self.request_review()
        self.assertEqual(response.status_code, 202, response.data)
        self.assertIs(
            self.draft_queue.call_args.args[0], draft_tasks.review_starting_frame_task
        )
        self.provider.assert_not_called()
        result = self.run_draft_task()
        self.assertEqual(result["verdict"], "needs_changes")
        self.scene.refresh_from_db()
        serialized = SceneSerializer(self.scene).data
        self.assertEqual(serialized["starting_frame_review"], result)
        self.assertEqual(serialized["starting_frame_status"], "needs_review")
        self.old.refresh_from_db()
        self.assertEqual(self.old.file.name, "images/old.mp4")
        self.scene_queue.assert_not_called()

    def test_comparison_contains_both_images_and_uses_project_model_and_usage(self):
        Image.new("RGB", (32, 32), "red").save(self.frame.parent / "cast.png")
        with review_comparison_sheet(self.scene, has_reference=True) as output, Image.open(output) as sheet:
            self.assertEqual(sheet.size, (1536, 800))
            self.assertGreater(sheet.getpixel((384, 416))[0], 200)
            self.assertGreater(sheet.getpixel((1152, 416))[2], 200)
        self.video.settings["gpt_model"] = "claude-example"
        self.video.save(update_fields=["settings"])
        self.scene.video = self.video

        def reply(*args, **kwargs):
            self.assertEqual(current_video.get().pk, self.video.pk)
            self.assertEqual(kwargs["user"], self.user)
            self.assertEqual(kwargs["gpt_model"], "claude-example")
            self.assertTrue(kwargs["reference_image"].read())
            self.assertIn("Milo at gate", args[0])
            return StringIO(json.dumps(self.review))

        self.provider.side_effect = reply
        review_starting_frame(self.scene, review_source_key(self.scene))
        self.assertIsNone(current_video.get())

    def test_other_users_invalid_assets_and_missing_images_cannot_queue_reviews(self):
        self.client.force_authenticate(user.make())
        self.assertEqual(self.request_review().status_code, 403)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.request_review(asset_id=str(uuid4())).status_code, 400)
        self.assertEqual(self.request_review(asset_id="invalid").status_code, 400)
        self.scene.starting_asset.file.delete(save=False)
        self.assertEqual(self.request_review().status_code, 400)
        self.draft_queue.assert_not_called()
        self.provider.assert_not_called()

    def test_legacy_generation_parameters_select_the_review_model(self):
        self.video.settings["generation_params"] = {"gpt_model": "claude-selected-model"}
        self.video.save(update_fields=["settings"])
        response = self.request_review()
        self.assertEqual(response.status_code, 202, response.data)
        self.run_draft_task()
        self.assertEqual(self.provider.call_args.kwargs["gpt_model"], "claude-selected-model")

    def test_legacy_series_episode_selects_the_review_model(self):
        baker.make(
            "series.SeriesEpisode",
            video=self.video,
            generation_params={"gpt_model": "gemini-episode-model"},
        )
        response = self.request_review()
        self.assertEqual(response.status_code, 202, response.data)
        self.run_draft_task()
        self.assertEqual(self.provider.call_args.kwargs["gpt_model"], "gemini-episode-model")

    def test_current_saved_review_is_invalidated_when_the_resolved_model_changes(self):
        self.scene.video = self.video
        self.video.settings["generation_params"] = {"gpt_model": "claude-selected-model"}
        self.video.save(update_fields=["settings"])
        review_starting_frame(self.scene, review_source_key(self.scene))
        self.scene.refresh_from_db()
        self.scene.video = self.video
        self.assertIsNotNone(SceneSerializer(self.scene).data["starting_frame_review"])
        self.video.settings["gpt_model"] = "gemini-new-model"
        self.assertIsNone(SceneSerializer(self.scene).data["starting_frame_review"])

    @override_settings(DEFAULT_GPT_MODEL="gpt-default-model")
    def test_legacy_project_without_saved_model_uses_and_fingerprints_the_default(self):
        self.scene.video = self.video
        source_key = review_source_key(self.scene)
        review_starting_frame(self.scene, source_key)
        self.assertEqual(self.provider.call_args.kwargs["gpt_model"], "gpt-default-model")
        with override_settings(DEFAULT_GPT_MODEL="gemini-new-default"):
            self.assertNotEqual(review_source_key(self.scene), source_key)

    def test_worker_rechecks_ownership(self):
        with self.assertRaises(type(self.scene).DoesNotExist):
            draft_tasks.review_starting_frame_task.run(
                str(user.make().pk),
                scene_id=str(self.scene.pk),
                source_key=review_source_key(self.scene),
            )
        self.provider.assert_not_called()

    def test_changed_source_is_rejected_before_spending_on_a_queued_review(self):
        self.request_review()
        self.scene.text = "A different action"
        self.scene.save(update_fields=["text"])
        with self.assertRaises(ValidationError):
            self.run_draft_task()
        self.provider.assert_not_called()

    def test_changes_during_review_do_not_save_stale_findings(self):
        def change_shot(*args, **kwargs):
            type(self.scene).objects.filter(pk=self.scene.pk).update(text="New action")
            return StringIO(json.dumps(self.review))

        self.provider.side_effect = change_shot
        with self.assertRaises(ValidationError):
            review_starting_frame(self.scene, review_source_key(self.scene))
        self.scene.refresh_from_db()
        self.assertNotIn("ai_review", self.scene.starting_frame_context)

    def test_current_saved_review_is_hidden_after_guidance_changes(self):
        review_starting_frame(self.scene, review_source_key(self.scene))
        self.scene.refresh_from_db()
        self.assertIsNotNone(SceneSerializer(self.scene).data["starting_frame_review"])
        self.video.settings["visual_continuity"] = "Milo now wears a yellow scarf"
        self.video.save(update_fields=["settings"])
        self.scene.video = self.video
        self.assertIsNone(SceneSerializer(self.scene).data["starting_frame_review"])

    def test_approval_does_not_invalidate_a_review(self):
        review_starting_frame(self.scene, review_source_key(self.scene))
        self.post("approve")
        self.scene.refresh_from_db()
        self.assertEqual(
            SceneSerializer(self.scene).data["starting_frame_review"]["verdict"],
            "needs_changes",
        )
        self.assertEqual(
            SceneSerializer(self.scene).data["starting_frame_status"], "approved"
        )

    def test_saved_review_is_hidden_if_reference_file_disappears(self):
        source_key = review_source_key(self.scene)
        review_starting_frame(self.scene, source_key)
        self.scene.refresh_from_db()
        self.assertIsNotNone(SceneSerializer(self.scene).data["starting_frame_review"])
        self.video.reference_image.delete(save=False)
        self.assertNotEqual(review_source_key(self.scene), source_key)
        self.assertIsNone(SceneSerializer(self.scene).data["starting_frame_review"])

    def test_missing_reference_or_changed_settings_do_not_spend_on_review(self):
        self.video.settings["visual_continuity"] = "New wardrobe"
        self.video.save(update_fields=["settings"])
        self.assertEqual(self.request_review().status_code, 400)
        self.video.settings.pop("visual_continuity")
        self.video.save(update_fields=["settings"])
        self.video.reference_image.delete(save=False)
        self.assertEqual(self.request_review().status_code, 400)
        self.draft_queue.assert_not_called()
        self.provider.assert_not_called()

    def test_malformed_or_contradictory_reviews_are_not_saved(self):
        for value in [
            "not JSON",
            [],
            {},
            {**self.review, "verdict": "excellent"},
            {**self.review, "verdict": "ready"},
            {**self.review, "findings": []},
            {**self.review, "findings": self.review["findings"] * 7},
            {**self.review, "summary": 42},
            {**self.review, "suggested_description": 42},
            {**self.review, "findings": [{**self.review["findings"][0], "issue": 42}]},
            {**self.review, "findings": [{**self.review["findings"][0], "fix": 42}]},
        ]:
            with self.subTest(value=value):
                self.provider.return_value = StringIO(json.dumps(value))
                with self.assertRaises(ValidationError):
                    review_starting_frame(self.scene, review_source_key(self.scene))
                self.scene.refresh_from_db()
                self.assertNotIn("ai_review", self.scene.starting_frame_context)

    def test_missing_provider_response_is_reported_as_invalid_review(self):
        self.provider.return_value = None
        with self.assertRaisesMessage(ValidationError, "AI returned an invalid starting frame review"):
            review_starting_frame(self.scene, review_source_key(self.scene))
        self.scene.refresh_from_db()
        self.assertNotIn("ai_review", self.scene.starting_frame_context)

    def test_ready_and_uncertain_verdicts_are_supported(self):
        for verdict in ["ready", "uncertain"]:
            with self.subTest(verdict=verdict):
                self.provider.return_value = StringIO(
                    json.dumps(
                        {
                            "verdict": verdict,
                            "summary": "No clear defects visible.",
                            "findings": [],
                            "suggested_description": "",
                        }
                    )
                )
                result = review_starting_frame(self.scene, review_source_key(self.scene))
                self.assertEqual(result["verdict"], verdict)

    def test_provider_failure_keeps_the_existing_review_and_approved_image(self):
        self.post("approve")
        self.scene.refresh_from_db()
        review_starting_frame(self.scene, review_source_key(self.scene))
        for error_type in [RuntimeError, ValueError, OSError]:
            with self.subTest(error_type=error_type):
                self.provider.side_effect = error_type("private provider details")
                with self.assertRaises(error_type):
                    review_starting_frame(self.scene, review_source_key(self.scene))
                self.assertIsNone(current_video.get())
        self.scene.refresh_from_db()
        serialized = SceneSerializer(self.scene).data
        self.assertEqual(
            serialized["starting_frame_review"]["verdict"], "needs_changes"
        )
        self.assertEqual(serialized["starting_frame_status"], "approved")

    def test_unreadable_image_is_reported_before_calling_the_provider(self):
        with self.video.reference_image.open("wb") as reference:
            reference.write(b"invalid image")
        with self.assertRaisesMessage(ValidationError, "The review images could not be read"):
            review_starting_frame(self.scene, review_source_key(self.scene))
        self.provider.assert_not_called()

    def test_optional_review_without_reference_checks_the_single_frame(self):
        self.video.settings.pop("character_references")
        self.video.settings["review_starting_frames"] = True
        self.video.reference_image = ""
        self.video.save(update_fields=["settings", "reference_image"])
        self.scene.video = self.video
        with patch("apps.videomanagement.services.scenes.visuals.openai_images.OpenAIImageProvider.generate", return_value=str(self.frame)):
            from apps.videomanagement.services.scenes.visuals import generate_new_image
            generate_new_image(self.old, self.video)
        self.scene.refresh_from_db()
        self.assertEqual(self.request_review().status_code, 202)
        self.run_draft_task()
        self.assertIn("No character reference was supplied", self.provider.call_args.args[0])
        self.scene.refresh_from_db()
        self.scene.video = self.video
        with review_comparison_sheet(self.scene, has_reference=False) as output, Image.open(output) as sheet:
            self.assertEqual(sheet.size, (768, 800))
        self.old.refresh_from_db()
        self.assertEqual(self.old.file.name, "images/old.mp4")

    def test_optional_reference_disappearing_during_review_rejects_stale_findings(self):
        self.video.settings.pop("character_references")
        self.video.settings["review_starting_frames"] = True
        self.video.save(update_fields=["settings"])
        self.scene.video = self.video

        def remove_reference(*args, **kwargs):
            self.assertNotIn("No character reference was supplied", args[0])
            with Image.open(kwargs["reference_image"]) as sheet:
                self.assertEqual(sheet.size, (1536, 800))
            self.video.reference_image.delete(save=False)
            return StringIO(json.dumps(self.review))

        self.provider.side_effect = remove_reference
        with self.assertRaisesMessage(ValidationError, "The frame or shot changed"):
            review_starting_frame(self.scene, review_source_key(self.scene))
        self.scene.refresh_from_db()
        self.assertNotIn("ai_review", self.scene.starting_frame_context)

    def test_prompt_uses_the_reference_decision_made_for_the_comparison_image(self):
        from apps.videomanagement.services.scenes import starting_frame_review

        comparison = starting_frame_review.review_comparison_sheet

        def remove_after_comparison(*args, **kwargs):
            output = comparison(*args, **kwargs)
            self.video.reference_image.delete(save=False)
            return output

        with patch.object(starting_frame_review, "review_comparison_sheet", side_effect=remove_after_comparison):
            with self.assertRaises(ValidationError):
                review_starting_frame(self.scene, review_source_key(self.scene))
        self.assertNotIn("No character reference was supplied", self.provider.call_args.args[0])
        self.scene.refresh_from_db()
        self.assertNotIn("ai_review", self.scene.starting_frame_context)
