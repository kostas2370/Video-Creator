from unittest.mock import patch

from django.urls import reverse

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import scene, scene_image
from ...models import SceneImage
from .base import ApiTestCase


class SceneViewTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for()
        self.scene = scene.make(video=self.video, text="the old line")

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


class SceneImageViewTests(ApiTestCase):
    def test_clears_the_file_of_an_ai_videos_image_but_keeps_the_scene(self):
        video_row = self.video_for()
        line = scene.make(video=video_row)
        image = scene_image.make(scene=line)

        response = self.client.delete(reverse("sceneimage-detail", args=[image.id]))

        self.assertEqual(response.status_code, 204)
        image.refresh_from_db()
        self.assertFalse(image.file)

    def test_removes_the_whole_scene_of_a_twitch_video(self):
        # The clip is the scene, so an empty one would render as a black gap.
        video_row = self.video_for(video_type="TWITCH")
        clip = scene.make(video=video_row)
        image = scene_image.make(scene=clip)

        self.client.delete(reverse("sceneimage-detail", args=[image.id]))

        self.assertFalse(video_row.scenes.filter(pk=clip.pk).exists())
