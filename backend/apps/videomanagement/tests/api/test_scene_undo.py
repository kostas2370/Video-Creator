from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import scene, scene_image
from apps.videomanagement.models import Scene, SceneImage
from apps.videomanagement.services.scenes.editing import archive_scene

from .base import ApiTestCase


class SceneUndoTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for(status="READY")
        self.first, self.second, self.third = scene.make(video=self.video, _quantity=3)
        self.ids = [str(row.pk) for row in (self.first, self.second, self.third)]
        self.image = scene_image.make(scene=self.second)

    def archive(self):
        return self.client.post(
            reverse("scene-archive", args=[self.second.pk]),
            {"scene_ids": self.ids},
            format="json",
        )

    def restore(self, expected=None):
        return self.client.post(
            reverse("scene-restore", args=[self.second.pk]),
            {
                "scene_ids": self.ids,
                "expected_scene_ids": expected
                if expected is not None
                else [self.ids[0], self.ids[2]],
            },
            format="json",
        )

    def test_removal_hides_scene_and_preserves_media_then_undo_restores_order(self):
        response = self.archive()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(Scene.objects.filter(pk=self.second.pk).exists())
        self.assertTrue(Scene.all_objects.filter(pk=self.second.pk).exists())
        self.assertTrue(SceneImage.objects.filter(pk=self.image.pk).exists())
        self.assertEqual(
            [str(row.pk) for row in self.video.scenes.all()], [self.ids[0], self.ids[2]]
        )
        response = self.restore()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([str(row.pk) for row in self.video.scenes.all()], self.ids)
        self.assertTrue(SceneImage.objects.filter(pk=self.image.pk).exists())

    def test_undo_refuses_changed_order_and_other_owners(self):
        self.assertEqual(self.archive().status_code, 200)
        self.assertEqual(
            self.restore(
                expected=list(reversed([self.ids[0], self.ids[2]]))
            ).status_code,
            409,
        )
        self.client.force_authenticate(user.make())
        self.assertEqual(self.restore().status_code, 403)
        self.assertFalse(Scene.objects.filter(pk=self.second.pk).exists())

    def test_rendering_blocks_removal_and_restore(self):
        self.video.status = "RENDERING"
        self.video.save(update_fields=["status"])
        self.assertEqual(self.archive().status_code, 409)
        self.video.status = "READY"
        self.video.save(update_fields=["status"])
        self.assertEqual(self.archive().status_code, 200)
        self.video.status = "RENDERING"
        self.video.save(update_fields=["status"])
        self.assertEqual(self.restore().status_code, 409)

    def test_archive_last_scene_and_restore_after_empty_project(self):
        for row in (self.first, self.second, self.third):
            archive_scene(row, list(self.video.scenes.values_list("pk", flat=True)))
        response = self.client.post(
            reverse("scene-restore", args=[self.second.pk]),
            {
                "scene_ids": [str(self.second.pk)],
                "expected_scene_ids": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            list(self.video.scenes.values_list("pk", flat=True)), [self.second.pk]
        )

    def test_archived_positions_do_not_block_new_scenes_or_reorder(self):
        self.assertEqual(self.archive().status_code, 200)
        extra = scene.make(video=self.video)
        ids = [str(extra.pk), self.ids[2], self.ids[0]]
        url = reverse("video-reorder-scenes", args=[self.video.pk])
        response = self.client.post(
            url,
            {
                "scene_ids": ids,
                "expected_scene_ids": [self.ids[0], self.ids[2], str(extra.pk)],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post(
            url,
            {
                "scene_ids": list(reversed(ids)),
                "expected_scene_ids": [self.ids[0], self.ids[2], str(extra.pk)],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual([str(row.pk) for row in self.video.scenes.all()], ids)
