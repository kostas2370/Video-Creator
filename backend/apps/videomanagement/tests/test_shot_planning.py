import io
import json
from copy import deepcopy
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.videomanagement.baker_recipes import scene_image, video
from apps.videomanagement.integrations.llm import get_reply, script_errors
from apps.videomanagement.schemas.shot_planning import ShotPlanSerializer
from apps.videomanagement.serializers.requests import StoryboardSerializer
from apps.videomanagement.services.scenes.narration import ensure_scene_rows
from apps.videomanagement.services.scenes.visuals import (
    continuation_frame,
    create_image_scene,
    generate_new_image,
    visual_generation_duration,
)
from apps.videomanagement.tests.api.base import ApiTestCase
from apps.videomanagement.utils.prompt_utils import build_script_prompt, script_lines
from apps.videomanagement.utils.timing import scene_timing

PLAN = {
    "shot_size": "CLOSE_UP",
    "camera_movement": "PUSH_IN",
    "subject_action": "Milo opens the wooden box.",
    "target_duration": 4.5,
}


def storyboard(plan=PLAN):
    shot = {
        "sentence": "Milo opens the box.",
        "image_description": "A fox beside a wooden box.",
    }
    if plan is not None:
        shot["shot_plan"] = deepcopy(plan)
    return {"title": "The box", "scenes": [{"scene": "Opening", "sentences": [shot]}]}


class ShotPlanValidationTests(SimpleTestCase):
    def test_approval_preserves_reviewed_plans_and_accepts_legacy_storyboards(self):
        for plan in (PLAN, None, {}):
            serializer = StoryboardSerializer(data=storyboard(plan))
            self.assertTrue(serializer.is_valid(), serializer.errors)
            shot = serializer.validated_data["scenes"][0]["sentences"][0]
            self.assertEqual(shot.get("shot_plan"), plan)

    def test_invalid_plans_are_rejected_by_approval_and_model_response_validation(self):
        for changes in (
            {"shot_size": "EXTREME"},
            {"camera_movement": "SPIN"},
            {"subject_action": "x" * 501},
            {"target_duration": -1},
            {"target_duration": 31},
            {"target_duration": float("nan")},
            {"target_duration": float("inf")},
        ):
            with self.subTest(changes=changes):
                draft = storyboard({**PLAN, **changes})
                self.assertFalse(StoryboardSerializer(data=draft).is_valid())
                self.assertIn("shot_plan", " ".join(script_errors(draft)))

    def test_optional_directions_and_duration_can_be_cleared(self):
        serializer = ShotPlanSerializer(
            data={
                "shot_size": "",
                "camera_movement": "",
                "subject_action": "",
                "target_duration": None,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_model_plan_is_retried_with_specific_feedback(self):
        with patch(
            "apps.videomanagement.integrations.llm.official_gpt_call",
            side_effect=[
                io.StringIO(json.dumps(storyboard({**PLAN, "target_duration": 90}))),
                io.StringIO(json.dumps(storyboard())),
            ],
        ) as call:
            result = get_reply("Make a video")
        self.assertEqual(result, storyboard())
        self.assertIn("target_duration", call.call_args.args[0])

    def test_ai_storyboard_prompt_requests_structured_plans_but_web_queries_stay_simple(
        self,
    ):
        for is_video in (False, True):
            prompt = build_script_prompt(image_mode="AI", video=is_video)
            shape = json.loads(prompt[prompt.index("{") : prompt.rindex("}") + 1])
            self.assertIn("shot_plan", shape["scenes"][0]["sentences"][0])
            self.assertIn("Actual narration controls", prompt)
        self.assertNotIn("shot_plan", build_script_prompt(image_mode="WEB"))

    def test_script_lines_keep_the_original_prompt_and_plan_separate(self):
        line = next(script_lines(storyboard()))
        self.assertEqual(line.shot_plan, PLAN)
        self.assertEqual(line.image_description, "A fox beside a wooden box.")


class ApplyShotPlanTests(TestCase):
    def project(self, *, narration=True, provider="OPENAI", plan=PLAN):
        return video.make(
            mode="AI",
            gpt_answer=storyboard(plan),
            settings={"narration": narration, "provider": provider},
        )

    def test_still_camera_direction_becomes_editor_motion_without_truncating_narration(
        self,
    ):
        vid = self.project()
        ensure_scene_rows(vid)
        scene = vid.scenes.get()
        self.assertEqual(scene.shot_plan, PLAN)
        self.assertEqual(scene.motion_style, "ZOOM_IN")
        self.assertNotIn("duration", scene.audio_settings)

    def test_silent_plan_sets_playback_and_provider_duration(self):
        vid = self.project(narration=False)
        ensure_scene_rows(vid)
        scene = vid.scenes.get()
        self.assertEqual(scene.audio_settings["duration"], 4.5)
        self.assertEqual(scene_timing(scene)["base_duration"], 4.5)
        self.assertEqual(visual_generation_duration(scene), 4.5)

    def test_video_plan_keeps_camera_motion_in_the_provider(self):
        vid = self.project(provider="runway")
        with patch(
            "apps.videomanagement.services.scenes.narration.ImageProviderRegistry.is_video",
            return_value=True,
        ):
            ensure_scene_rows(vid)
        self.assertEqual(vid.scenes.get().motion_style, "NONE")

    def test_resume_preserves_manual_motion_and_duration_edits(self):
        vid = self.project(narration=False)
        ensure_scene_rows(vid)
        scene = vid.scenes.get()
        scene.motion_style = "PAN_LEFT"
        scene.audio_settings = {"duration": 8}
        scene.save()
        ensure_scene_rows(vid)
        scene.refresh_from_db()
        self.assertEqual(scene.motion_style, "PAN_LEFT")
        self.assertEqual(scene.audio_settings, {"duration": 8})
        self.assertEqual(visual_generation_duration(scene), 8)
        self.assertEqual(scene.shot_plan, PLAN)

    def test_silent_continuation_uses_the_planned_visible_endpoint(self):
        vid = self.project(narration=False, provider="runway")
        ensure_scene_rows(vid)
        with patch(
            "apps.videomanagement.services.scenes.visuals.still_from_video"
        ) as frame:
            continuation_frame(vid, vid.scenes.get().text, "fox.mp4")
        self.assertEqual(frame.call_args.kwargs["end_time"], 4.5)

    def test_web_generation_ignores_cinematic_plans(self):
        vid = self.project(narration=False, provider="bing")
        vid.mode = "WEB"
        ensure_scene_rows(vid)
        scene = vid.scenes.get()
        self.assertEqual(scene.shot_plan, {})
        self.assertEqual(scene.motion_style, "NONE")
        self.assertEqual(scene.audio_settings, {})

    def test_creation_and_regeneration_apply_the_plan_once_without_changing_saved_prompt(
        self,
    ):
        vid = self.project(narration=False)
        ensure_scene_rows(vid)
        row = vid.scenes.get()
        with patch(
            "apps.videomanagement.services.scenes.visuals.ImageProviderRegistry.resolve"
        ) as resolve:
            provider = resolve.return_value
            provider.return_value = "images/fox.png"
            create_image_scene(
                vid,
                "A fox beside a wooden box.",
                row.text,
                "output",
                mode="AI",
                provider="OPENAI",
            )
            visual = row.scene_images.get()
            generate_new_image(visual, vid, reference=None)
        self.assertEqual(provider.call_count, 2)
        for call in provider.call_args_list:
            prompt = call.args[0]
            self.assertEqual(prompt.count("REVIEWED SHOT PLAN"), 1)
            self.assertIn("Shot size: close up", prompt)
            self.assertIn(PLAN["subject_action"], prompt)
            self.assertNotIn("Camera movement:", prompt)
            self.assertEqual(call.kwargs["duration"], 4.5)
        self.assertEqual(visual.prompt, "A fox beside a wooden box.")

    def test_video_generation_gets_camera_directions_and_actual_narration_duration(
        self,
    ):
        vid = self.project(provider="runway")
        with patch(
            "apps.videomanagement.services.scenes.narration.ImageProviderRegistry.is_video",
            return_value=True,
        ):
            ensure_scene_rows(vid)
        row = vid.scenes.get()
        visual = scene_image.make(scene=row, prompt="A fox beside a wooden box.")
        with (
            patch(
                "apps.videomanagement.services.scenes.visuals.ImageProviderRegistry.resolve"
            ) as resolve,
            patch(
                "apps.videomanagement.services.scenes.visuals.ImageProviderRegistry.is_video",
                return_value=True,
            ),
            patch(
                "apps.videomanagement.services.scenes.visuals.scene_narration_duration",
                return_value=7.2,
            ),
        ):
            resolve.return_value.return_value = "images/fox.mp4"
            generate_new_image(visual, vid, reference=None)
        call = resolve.return_value.call_args
        self.assertIn("Camera movement: push in", call.args[0])
        self.assertEqual(call.kwargs["duration"], 7.2)


class ShotPlanApprovalTests(ApiTestCase):
    def test_reviewed_plan_survives_approval_and_is_ready_for_the_worker(self):
        vid = self.video_for(
            status="REVIEW",
            mode="AI",
            settings={"generation_params": {"message": "A fox", "image_mode": "AI"}},
        )
        with patch("apps.videomanagement.tasks.generate_video_task.delay") as queued:
            response = self.client.post(
                reverse("video-approve-script", args=[vid.pk]),
                storyboard(),
                format="json",
            )
        self.assertEqual(response.status_code, 202, response.data)
        queued.assert_called_once()
        vid.refresh_from_db()
        self.assertEqual(next(script_lines(vid.gpt_answer)).shot_plan, PLAN)
        ensure_scene_rows(vid)
        self.assertEqual(vid.scenes.get().shot_plan, PLAN)

    def test_invalid_reviewed_plan_does_not_queue_paid_generation(self):
        vid = self.video_for(
            status="REVIEW",
            mode="AI",
            settings={"generation_params": {"image_mode": "AI"}},
        )
        with patch("apps.videomanagement.tasks.generate_video_task.delay") as queued:
            response = self.client.post(
                reverse("video-approve-script", args=[vid.pk]),
                storyboard({**PLAN, "target_duration": 90}),
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        queued.assert_not_called()
        vid.refresh_from_db()
        self.assertEqual(vid.status, "REVIEW")
