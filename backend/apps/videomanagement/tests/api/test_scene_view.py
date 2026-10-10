from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from rest_framework.routers import SimpleRouter

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import scene, scene_image
from ...models import SceneImage
from ...views.scene_view import SceneView
from .base import ApiTestCase


class SceneViewTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for()
        self.scene = scene.make(video=self.video, text="the old line")

    def test_timing_saves_without_charging_or_regenerating(self):
        self.user.generation_limit_for_ai = 0
        self.user.save()
        with patch("apps.videomanagement.views.scene_view.update_scene") as regenerate:
            response = self.client.patch(reverse("scene-timing", args=[self.scene.pk]), {"pause_after": 0.75}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.pause_after, 0.75)
        self.assertEqual(response.data["timing"]["duration"] - response.data["timing"]["base_duration"], 0.75)
        self.user.refresh_from_db()
        self.assertEqual(self.user.generation_limit_for_ai, 0)
        regenerate.assert_not_called()

    def test_timing_rejects_invalid_pauses(self):
        for payload in ({}, {"pause_after": None}, {"pause_after": -1}, {"pause_after": 11}, {"pause_after": "NaN"}, {"pause_after": "Infinity"}):
            response = self.client.patch(reverse("scene-timing", args=[self.scene.pk]), payload, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.pause_after, 0)

    def test_timing_is_blocked_while_processing_and_for_other_users(self):
        url = reverse("scene-timing", args=[self.scene.pk])
        for state in ("GENERATION", "RENDERING", "REVIEW"):
            self.video.status = state
            self.video.save()
            self.assertEqual(self.client.patch(url, {"pause_after": 1}, format="json").status_code, 409)
        foreign = scene.make(video=self.video_for(owner=user.make()))
        self.assertEqual(self.client.patch(reverse("scene-timing", args=[foreign.pk]), {"pause_after": 1}, format="json").status_code, 403)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.patch(url, {"pause_after": 1}, format="json").status_code, 401)

    def test_transition_saves_without_charging_or_regenerating_media(self):
        self.user.generation_limit_for_ai = 0
        self.user.save()
        with patch("apps.videomanagement.views.scene_view.update_scene") as regenerate:
            response = self.client.patch(reverse("scene-transition", args=[self.scene.pk]),
                                         {"transition_after": "CUT"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.transition_after, "CUT")
        self.assertEqual(self.scene.text, "the old line")
        self.user.refresh_from_db()
        self.assertEqual(self.user.generation_limit_for_ai, 0)
        regenerate.assert_not_called()

    def test_dissolve_duration_and_reset_to_video_default(self):
        url = reverse("scene-transition", args=[self.scene.pk])
        response = self.client.patch(url, {"transition_after": "DISSOLVE", "transition_duration": 0.75}, format="json")
        self.assertEqual(response.status_code, 200)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.transition_duration, 0.75)
        response = self.client.patch(url, {"transition_after": "DEFAULT", "transition_duration": None}, format="json")
        self.assertEqual(response.status_code, 200)
        self.scene.refresh_from_db()
        self.assertIsNone(self.scene.transition_duration)
        self.assertEqual(self.scene.transition_after, "DEFAULT")

    def test_transition_rejects_invalid_durations(self):
        for value in (-1, 0, 4, "NaN", "Infinity"):
            response = self.client.patch(reverse("scene-transition", args=[self.scene.pk]),
                                         {"transition_after": "DISSOLVE", "transition_duration": value}, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        self.scene.refresh_from_db()
        self.assertIsNone(self.scene.transition_duration)

    def test_transition_rejects_unsupported_effects(self):
        response = self.client.patch(reverse("scene-transition", args=[self.scene.pk]),
                                     {"transition_after": "SPIN"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.transition_after, "DEFAULT")

    def test_transition_is_blocked_while_processing(self):
        for state in ("GENERATION", "RENDERING", "REVIEW"):
            self.video.status = state
            self.video.save()
            response = self.client.patch(reverse("scene-transition", args=[self.scene.pk]),
                                         {"transition_after": "CUT"}, format="json")
            self.assertEqual(response.status_code, 409)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.transition_after, "DEFAULT")

    def test_transition_cannot_edit_another_users_scene(self):
        foreign = scene.make(video=self.video_for(owner=user.make()))
        response = self.client.patch(reverse("scene-transition", args=[foreign.pk]),
                                     {"transition_after": "CUT"}, format="json")
        self.assertEqual(response.status_code, 403)
        foreign.refresh_from_db()
        self.assertEqual(foreign.transition_after, "DEFAULT")

    def test_rewrites_a_line_and_charges_for_it(self):
        before = self.user.generation_limit_for_ai

        with patch("apps.videomanagement.services.SceneServices.update"):
            response = self.client.patch(
                reverse("scene-detail", args=[self.scene.id]),
                {"text": "a new line"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["text"], "a new line")
        self.user.refresh_from_db()
        self.assertAlmostEqual(self.user.generation_limit_for_ai, before - 0.01)

    def test_asks_the_model_for_a_rewrite_and_charges_more_for_it(self):
        before = self.user.generation_limit_for_ai

        with patch(
            "apps.videomanagement.services.SceneServices.get_update_sentence",
            return_value="a funnier line",
        ):
            response = self.client.patch(
                reverse("scene-generate", args=[self.scene.id]),
                {"text": "make it funnier"},
                format="json",
            )

        self.assertEqual(response.data["text"], "a funnier line")
        self.user.refresh_from_db()
        self.assertAlmostEqual(self.user.generation_limit_for_ai, before - 0.03)

    def test_rejects_invalid_generation_inputs_before_work_or_charging(self):
        actions = (
            ("scene-detail", "text", self.client.patch, "update_scene"),
            ("scene-generate", "text", self.client.patch, "generate_scene"),
            ("scene-generate-image-scene", "image_description", self.client.post, "generate_new_image"),
        )
        before = self.user.generation_limit_for_ai
        for route, field, method, service in actions:
            for payload in ({}, {field: None}, {field: " "}, {field: []}, {field: "x" * 2001}):
                with self.subTest(route=route, payload=payload):
                    with patch("apps.videomanagement.views.scene_view." + service) as work:
                        response = method(
                            reverse(route, args=[self.scene.pk]), payload, format="json"
                        )
                    self.assertEqual(response.status_code, 400)
                    work.assert_not_called()
        self.user.refresh_from_db()
        self.assertEqual(self.user.generation_limit_for_ai, before)
        self.assertFalse(SceneImage.objects.filter(scene=self.scene).exists())

    def test_stale_user_instances_each_pay_without_overwriting_account_settings(self):
        users = [get_user_model().objects.get(pk=self.user.pk) for _ in range(2)]
        before = self.user.generation_limit_for_ai
        get_user_model().objects.filter(pk=self.user.pk).update(use_service_api_keys=False)
        with patch("apps.videomanagement.views.scene_view.generate_scene", return_value="rewritten"):
            for caller in users:
                self.client.force_authenticate(caller)
                response = self.client.patch(
                    reverse("scene-generate", args=[self.scene.pk]),
                    {"text": "rewrite"}, format="json",
                )
                self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertAlmostEqual(self.user.generation_limit_for_ai, before - 0.06)
        self.assertFalse(self.user.use_service_api_keys)

    def test_a_stale_permission_check_cannot_spend_exhausted_credit(self):
        self.user.generation_limit_for_ai = 0.21
        self.user.save(update_fields=["generation_limit_for_ai"])
        callers = [get_user_model().objects.get(pk=self.user.pk) for _ in range(2)]
        url = reverse("scene-generate", args=[self.scene.pk])
        with patch("apps.videomanagement.views.scene_view.generate_scene", return_value="rewritten") as work:
            self.client.force_authenticate(callers[0])
            self.assertEqual(self.client.patch(url, {"text": "rewrite"}).status_code, 200)
            self.client.force_authenticate(callers[1])
            self.assertEqual(self.client.patch(url, {"text": "rewrite"}).status_code, 403)
            work.assert_called_once()
        self.user.refresh_from_db()
        self.assertAlmostEqual(self.user.generation_limit_for_ai, 0.18)

    def test_failed_generation_refunds_the_reservation(self):
        before = self.user.generation_limit_for_ai
        actions = (
            ("scene-detail", {"text": "new"}, self.client.patch, "update_scene"),
            ("scene-generate", {"text": "rewrite"}, self.client.patch, "generate_scene"),
            ("scene-generate-image-scene", {"image_description": "cat"}, self.client.post, "generate_new_image"),
        )
        for route, payload, method, service in actions:
            with self.subTest(route=route):
                with patch("apps.videomanagement.views.scene_view." + service, side_effect=RuntimeError("Unavailable")):
                    with self.assertRaises(RuntimeError):
                        method(reverse(route, args=[self.scene.pk]), payload, format="json")
                self.user.refresh_from_db()
                self.assertAlmostEqual(self.user.generation_limit_for_ai, before)

    def test_attaches_an_uploaded_image_to_a_scene_with_none(self):
        response = self.client.post(
            reverse("scene-change-image-scene", args=[self.scene.id]),
            {"with_audio": False},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(SceneImage.objects.filter(scene=self.scene).exists())

    def test_replaces_the_visual_of_a_scene_that_has_one(self):
        image = scene_image.make(scene=self.scene, with_audio=False)

        response = self.client.post(
            f"{reverse('scene-change-image-scene', args=[self.scene.id])}"
            f"?scene_image={image.id}",
            {"with_audio": True},
        )

        self.assertEqual(response.status_code, 200)
        image.refresh_from_db()
        self.assertTrue(image.with_audio)

    def test_uploads_and_replaces_a_file_using_multipart(self):
        url = reverse("scene-change-image-scene", args=[self.scene.id])
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                url,
                {"image": SimpleUploadedFile("first.png", b"first"), "with_audio": "0"},
                format="multipart",
            )
            self.assertEqual(response.status_code, 200)
            image = SceneImage.objects.get(scene=self.scene)
            self.assertFalse(image.with_audio)
            with image.file.open("rb") as uploaded:
                self.assertEqual(uploaded.read(), b"first")

            response = self.client.post(
                f"{url}?scene_image={image.pk}",
                {"image": SimpleUploadedFile("second.png", b"second"), "with_audio": "1"},
                format="multipart",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(SceneImage.objects.filter(scene=self.scene).count(), 1)
            image.refresh_from_db()
            self.assertTrue(image.with_audio)
            with image.file.open("rb") as uploaded:
                self.assertEqual(uploaded.read(), b"second")

    def test_invalid_image_ids_return_400_and_missing_images_return_404(self):
        url = reverse("scene-change-image-scene", args=[self.scene.id])
        for image_id in ("invalid", "0", "-1", "1.5"):
            with self.subTest(image_id=image_id):
                response = self.client.post(f"{url}?scene_image={image_id}", {})
                self.assertEqual(response.status_code, 400)

        image = scene_image.make(scene=self.scene)
        image_id = image.pk
        image.delete()
        response = self.client.post(f"{url}?scene_image={image_id}", {})
        self.assertEqual(response.status_code, 404)

    def test_audio_only_updates_still_accept_json(self):
        image = scene_image.make(scene=self.scene, with_audio=False)
        url = reverse("scene-change-image-scene", args=[self.scene.id])
        response = self.client.post(
            f"{url}?scene_image={image.pk}", {"with_audio": True}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        image.refresh_from_db()
        self.assertTrue(image.with_audio)

    def test_regenerates_a_scenes_image_and_charges_for_it(self):
        scene_image.make(scene=self.scene)
        before = self.user.generation_limit_for_ai

        with patch(
            "apps.videomanagement.views.scene_view.generate_new_image"
        ) as generate:
            response = self.client.post(
                reverse("scene-generate-image-scene", args=[self.scene.id]),
                {"image_description": "a cat"},
            )

        self.assertEqual(response.status_code, 200)
        generate.assert_called_once()
        self.user.refresh_from_db()
        self.assertAlmostEqual(self.user.generation_limit_for_ai, before - 0.08)

    def test_will_not_regenerate_an_image_with_nothing_to_go_on(self):
        response = self.client.post(
            reverse("scene-generate-image-scene", args=[self.scene.id]), {}
        )

        self.assertEqual(response.status_code, 400)

    def test_deletes_a_scene(self):
        response = self.client.delete(reverse("scene-detail", args=[self.scene.id]))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(self.video.scenes.filter(pk=self.scene.pk).exists())

    def test_will_not_touch_a_scene_of_someone_elses_video(self):
        stranger_video = self.video_for(owner=user.make())
        theirs = scene.make(video=stranger_video)

        response = self.client.delete(reverse("scene-detail", args=[theirs.id]))

        self.assertEqual(response.status_code, 403)

    def test_image_actions_reject_foreign_scenes_without_changes_or_charges(self):
        foreign_scene = scene.make(video=self.video_for(owner=user.make()))
        image = scene_image.make(scene=foreign_scene, with_audio=False)
        balance = self.user.generation_limit_for_ai
        for action in ("change-image-scene", "generate-image-scene"):
            with self.subTest(action=action):
                with patch("apps.videomanagement.views.scene_view.generate_new_image") as generate:
                    response = self.client.post(
                        f"{reverse('scene-' + action, args=[foreign_scene.id])}?scene_image={image.id}",
                        {"with_audio": True, "image_description": "changed"},
                    )
                self.assertEqual(response.status_code, 403)
                generate.assert_not_called()
                image.refresh_from_db()
                self.assertFalse(image.with_audio)
                self.assertEqual(image.prompt, "an image description")
                self.user.refresh_from_db()
                self.assertEqual(self.user.generation_limit_for_ai, balance)

    def test_cannot_target_an_image_from_a_different_scene(self):
        for owner in (self.user, user.make()):
            with self.subTest(owner=owner.pk):
                other = scene.make(video=self.video_for(owner=owner))
                image = scene_image.make(scene=other, with_audio=False)
                response = self.client.post(
                    f"{reverse('scene-change-image-scene', args=[self.scene.id])}?scene_image={image.id}",
                    {"with_audio": True},
                )
                self.assertEqual(response.status_code, 404)
                image.refresh_from_db()
                self.assertFalse(image.with_audio)

    def test_generation_without_an_existing_image_uses_the_authorized_video(self):
        with patch("apps.videomanagement.views.scene_view.generate_new_image") as generate:
            response = self.client.post(
                reverse("scene-generate-image-scene", args=[self.scene.id]),
                {"image_description": "a cat"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(generate.call_args.args[0].scene, self.scene)
        self.assertEqual(generate.call_args.args[1], self.video)

    def test_retry_returns_missing_status_when_narration_is_still_unavailable(self):
        with patch("apps.videomanagement.utils.audio_utils.narrate_scene", side_effect=RuntimeError("Provider unavailable")):
            response = self.client.patch(
                reverse("scene-detail", args=[self.scene.id]),
                {"text": self.scene.text}, format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["narration_status"], "missing")
        self.assertEqual(response.data["text"], self.scene.text)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.text, "the old line")

    def test_retry_reports_available_status_after_audio_is_generated(self):
        with patch("apps.videomanagement.services.SceneServices.update"):
            with patch("apps.videomanagement.serializers.stored_file_exists", return_value=True):
                response = self.client.patch(
                    reverse("scene-detail", args=[self.scene.id]),
                    {"text": self.scene.text}, format="json",
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["narration_status"], "available")


class SceneImageSchemaTests(SimpleTestCase):
    def test_schema_exposes_a_writable_multipart_file_and_200_response(self):
        router = SimpleRouter()
        router.register("scenes", SceneView, basename="scene")
        schema = OpenAPISchemaGenerator(
            info=openapi.Info(title="Scenes", default_version="v1"),
            patterns=router.urls,
        ).get_schema(request=None, public=True)
        operation = schema.paths["/scenes/{id}/change_image_scene/"]["post"]
        self.assertIn("multipart/form-data", operation["consumes"])
        parameters = {item["name"]: item for item in operation["parameters"]}
        self.assertEqual(parameters["image"]["in"], "formData")
        self.assertEqual(parameters["image"]["type"], "file")
        self.assertEqual(parameters["scene_image"]["in"], "query")
        self.assertEqual(parameters["scene_image"]["type"], "string")
        self.assertIn("200", operation["responses"])
        self.assertNotIn("201", operation["responses"])


class SceneImageViewTests(ApiTestCase):
    def test_clears_the_file_of_an_ai_videos_image_but_keeps_the_scene(self):
        video_row = self.video_for()
        line = scene.make(video=video_row)
        image = scene_image.make(scene=line)

        response = self.client.delete(reverse("sceneimage-detail", args=[image.id]))

        self.assertEqual(response.status_code, 204)
        image.refresh_from_db()
        self.assertFalse(image.file)
