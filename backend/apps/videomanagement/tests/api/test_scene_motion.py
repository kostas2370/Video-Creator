from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from ...baker_recipes import scene
from ...models import VideoStatus
from .base import ApiTestCase


class SceneMotionTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for(status="READY")
        self.scene = scene.make(video=self.video)
        self.url = reverse("scene-motion", args=[self.scene.pk])

    def test_saves_motion_without_generating_media_or_charging(self):
        self.user.generation_limit_for_ai = 0
        self.user.save()
        response = self.client.patch(
            self.url,
            {"motion_style": "PAN_LEFT", "motion_intensity": "MEDIUM"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.motion_style, "PAN_LEFT")
        self.assertEqual(self.scene.motion_intensity, "MEDIUM")
        self.assertEqual(response.data["motion_style"], "PAN_LEFT")
        self.user.refresh_from_db()
        self.assertEqual(self.user.generation_limit_for_ai, 0)
        self.scene_queue.assert_not_called()

    def test_invalid_choices_do_not_change_scene(self):
        for changes in (
            {"motion_style": "SPIN"},
            {"motion_style": "ZOOM_IN", "motion_intensity": "extreme"},
        ):
            self.assertEqual(
                self.client.patch(self.url, changes, format="json").status_code, 400
            )
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.motion_style, "NONE")

    def test_foreign_scene_cannot_be_edited(self):
        other = scene.make(video=self.video_for(owner=user.make(), status="READY"))
        response = self.client.patch(
            reverse("scene-motion", args=[other.pk]),
            {"motion_style": "AUTO"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        other.refresh_from_db()
        self.assertEqual(other.motion_style, "NONE")

    def test_processing_and_review_block_changes(self):
        for status in (
            VideoStatus.GENERATION,
            VideoStatus.RENDERING,
            VideoStatus.REVIEW,
        ):
            self.video.status = status
            self.video.save()
            self.assertEqual(
                self.client.patch(
                    self.url, {"motion_style": "AUTO"}, format="json"
                ).status_code,
                409,
            )
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.motion_style, "NONE")
