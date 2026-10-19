
from unittest.mock import patch

from django.urls import reverse

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import scene, scene_image
from ...models import VideoStatus
from .base import ApiTestCase


class SceneMotionTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for(status="READY")
        self.scene = scene.make(video=self.video)
        self.url = reverse("scene-motion", args=[self.scene.pk])

    def test_saves_motion_without_generating_media(self):
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


class BulkAutoMotionTests(ApiTestCase):
    def setUp(self):
        super().setUp()

        self.video = self.video_for(status="READY")
        self.images = scene.make(video=self.video, motion_style="ZOOM_OUT", _quantity=2)
        for row in self.images:
            scene_image.make(scene=row, file="still.PNG")
        self.clip = scene.make(video=self.video, motion_style="PAN_UP")
        scene_image.make(scene=self.clip, file="clip.mp4")
        self.empty = scene.make(video=self.video)
        self.url = reverse("video-auto-motion", args=[self.video.pk])

    def test_applies_only_to_images_without_generating(self):
        response = self.client.patch(
            self.url, {"motion_intensity": "STRONG"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["scenes"]), 4)
        for row in self.images:
            row.refresh_from_db()
            self.assertEqual(
                (row.motion_style, row.motion_intensity), ("AUTO", "STRONG")
            )
        self.clip.refresh_from_db()
        self.empty.refresh_from_db()
        self.assertEqual(self.clip.motion_style, "PAN_UP")
        self.assertEqual(self.empty.motion_style, "NONE")
        self.scene_queue.assert_not_called()

    def test_invalid_intensity_changes_nothing(self):
        for data in ({}, {"motion_intensity": "EXTREME"}):
            self.assertEqual(
                self.client.patch(self.url, data, format="json").status_code, 400
            )
        for row in self.images:
            row.refresh_from_db()
            self.assertEqual(row.motion_style, "ZOOM_OUT")

    def test_foreign_video_cannot_be_edited(self):
        other = self.video_for(owner=user.make(), status="READY")
        response = self.client.patch(
            reverse("video-auto-motion", args=[other.pk]),
            {"motion_intensity": "SUBTLE"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_processing_and_review_block_bulk_changes(self):
        for state in (
            VideoStatus.GENERATION,
            VideoStatus.RENDERING,
            VideoStatus.REVIEW,
        ):
            self.video.status = state
            self.video.save()
            self.assertEqual(
                self.client.patch(
                    self.url, {"motion_intensity": "SUBTLE"}, format="json"
                ).status_code,
                409,
            )
        for row in self.images:
            row.refresh_from_db()
            self.assertEqual(row.motion_style, "ZOOM_OUT")

    def test_reapplying_unchanged_auto_does_not_publish_an_update(self):

        self.client.patch(self.url, {"motion_intensity": "SUBTLE"}, format="json")
        self.video.refresh_from_db()
        updated = self.video.updated_at
        with patch("apps.videomanagement.services.scenes.editing.publish_update") as publish:
            response = self.client.patch(
                self.url, {"motion_intensity": "SUBTLE"}, format="json"
            )
        self.assertEqual(response.status_code, 200)
        publish.assert_not_called()
        self.video.refresh_from_db()
        self.assertEqual(self.video.updated_at, updated)
