from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.core.files.base import ContentFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import scene, scene_image
from apps.videomanagement.models import MediaAsset, Scene, SceneImage
from apps.videomanagement.services.scenes.editing import archive_scene
from apps.videomanagement.services.scenes.recovery import purge_expired_scenes

from .base import ApiTestCase


class SceneRecoveryTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.video = self.video_for(status="READY")
        self.first, self.removed, self.last = scene.make(video=self.video, _quantity=3)
        self.list_url = reverse("video-deleted-scenes", args=[self.video.pk])
        self.restore_url = reverse("scene-restore", args=[self.removed.pk])

    def archive(self, row=None, age=None):
        row = row or self.removed
        archive_scene(row, list(self.video.scenes.values_list("pk", flat=True)))
        if age is not None:
            Scene.all_objects.filter(pk=row.pk).update(archived_at=timezone.now() - age)

    def test_recently_deleted_lists_deadline_and_restores_after_reload(self):
        self.archive()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        item = response.data["results"][0]
        self.assertEqual(str(item["id"]), str(self.removed.pk))
        self.assertEqual(item["position"], 2)
        self.assertAlmostEqual(
            (item["expires_at"] - item["archived_at"]).total_seconds(), 7 * 86400
        )
        response = self.client.post(
            self.restore_url,
            {"expected_scene_ids": [str(self.first.pk), str(self.last.pk)]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            list(self.video.scenes.values_list("pk", flat=True)),
            [self.first.pk, self.removed.pk, self.last.pk],
        )
        self.assertEqual(self.client.get(self.list_url).data["count"], 0)

    def test_expired_scenes_are_not_listed_or_restorable_before_cleanup(self):
        self.archive(age=timedelta(days=7, seconds=1))
        self.assertEqual(self.client.get(self.list_url).data["count"], 0)
        response = self.client.post(
            self.restore_url,
            {"expected_scene_ids": [str(self.first.pk), str(self.last.pk)]},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Scene.all_objects.filter(pk=self.removed.pk).exists())

    def test_recovery_is_private_to_video_owner(self):
        self.archive()
        self.client.force_authenticate(user.make())
        self.assertEqual(self.client.get(self.list_url).status_code, 404)
        self.assertEqual(
            self.client.post(
                self.restore_url, {"expected_scene_ids": []}, format="json"
            ).status_code,
            403,
        )

    def test_delete_endpoint_also_uses_recovery_window(self):
        response = self.client.delete(reverse("scene-detail", args=[self.removed.pk]))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Scene.objects.filter(pk=self.removed.pk).exists())
        self.assertEqual(self.client.get(self.list_url).data["count"], 1)

    def test_cleanup_deletes_expired_rows_and_unshared_files_only(self):
        self.removed.voiceover.save("expired.wav", ContentFile(b"unused audio"))
        file = self.removed.voiceover
        visual = scene_image.make(scene=self.removed)
        asset_id = visual.asset_id
        self.archive(age=timedelta(days=8))
        with self.captureOnCommitCallbacks(execute=True):
            result = purge_expired_scenes()
        self.assertEqual(result["deleted"], 1)
        self.assertFalse(Scene.all_objects.filter(pk=self.removed.pk).exists())
        self.assertFalse(SceneImage.objects.filter(pk=visual.pk).exists())
        self.assertTrue(Scene.objects.filter(pk=self.first.pk).exists())
        self.assertTrue(MediaAsset.objects.filter(pk=asset_id).exists())
        self.assertFalse(file.storage.exists(file.name))
        self.assertEqual(purge_expired_scenes()["deleted"], 0)

    def test_shared_narration_survives_cleanup(self):
        self.removed.voiceover.save("shared.wav", ContentFile(b"shared audio"))
        name = self.removed.voiceover.name
        self.first.voiceover = name
        self.first.save(update_fields=["voiceover"])
        self.archive(age=timedelta(days=8))
        with self.captureOnCommitCallbacks(execute=True):
            purge_expired_scenes()
        self.assertTrue(self.first.voiceover.storage.exists(name))

    def test_library_reference_protects_a_scene_file(self):
        self.removed.voiceover.save("library.wav", ContentFile(b"library audio"))
        name = self.removed.voiceover.name
        asset = MediaAsset.objects.create(
            created_by=self.user, title="Saved narration", file=name, kind="AUDIO"
        )
        self.archive(age=timedelta(days=8))
        with self.captureOnCommitCallbacks(execute=True):
            purge_expired_scenes()
        self.assertTrue(asset.file.storage.exists(name))

    def test_cleanup_skips_processing_and_preserves_unexpired_scenes(self):
        self.archive(age=timedelta(days=8))
        self.archive(self.last, age=timedelta(days=6))
        self.video.status = "RENDERING"
        self.video.save(update_fields=["status"])
        self.assertEqual(purge_expired_scenes()["deleted"], 0)
        self.video.status = "READY"
        self.video.save(update_fields=["status"])
        self.assertEqual(purge_expired_scenes()["deleted"], 1)
        self.assertTrue(Scene.all_objects.filter(pk=self.last.pk).exists())

    def test_daily_task_is_registered(self):
        schedule = settings.CELERY_BEAT_SCHEDULE["purge-expired-deleted-scenes"]
        self.assertEqual(
            schedule["task"], "apps.videomanagement.tasks.purge_deleted_scenes"
        )
        self.assertEqual(schedule["schedule"], 86400)

    def test_another_archived_scene_protects_shared_audio(self):
        self.removed.voiceover.save("retained.wav", ContentFile(b"retained audio"))
        name = self.removed.voiceover.name
        self.last.voiceover = name
        self.last.save(update_fields=["voiceover"])
        self.archive(age=timedelta(days=8))
        self.archive(self.last, age=timedelta(days=6))
        with self.captureOnCommitCallbacks(execute=True):
            purge_expired_scenes()
        self.assertTrue(self.last.voiceover.storage.exists(name))

    def test_video_deletion_also_removes_archived_scene_rows(self):
        self.archive()
        video_id = self.video.pk
        self.video.delete()
        self.assertFalse(Scene.all_objects.filter(video_id=video_id).exists())

    def test_large_cleanup_backlog_schedules_a_followup(self):
        from apps.videomanagement.tasks import purge_deleted_scenes

        with (
            patch(
                "apps.videomanagement.services.scenes.recovery.purge_expired_scenes",
                return_value={"deleted": 500, "examined": 500},
            ),
            patch.object(purge_deleted_scenes, "apply_async") as queue,
        ):
            self.assertEqual(purge_deleted_scenes.run()["deleted"], 500)
        queue.assert_called_once_with(countdown=30)

    def test_empty_cleanup_does_not_keep_scheduling_itself(self):
        from apps.videomanagement.tasks import purge_deleted_scenes

        with (
            patch(
                "apps.videomanagement.services.scenes.recovery.purge_expired_scenes",
                return_value={"deleted": 0, "examined": 0},
            ),
            patch.object(purge_deleted_scenes, "apply_async") as queue,
        ):
            purge_deleted_scenes.run()
        queue.assert_not_called()
