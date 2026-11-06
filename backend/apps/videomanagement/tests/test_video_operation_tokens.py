from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.videomanagement.baker_recipes import scene, voice_model
from apps.videomanagement.models import Video
from apps.videomanagement.services.scenes.jobs import queue_scene_job, restore_video
from apps.videomanagement.services.videos.recovery import _refresh_heartbeat
from apps.videomanagement.tasks import (
    _mark_failed,
    generate_scene_image_task,
    reap_stalled_videos,
    regenerate_narration_task,
)

from .api.base import ApiTestCase


class VideoOperationTokenTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user.use_service_api_keys = False
        self.user.save(update_fields=["use_service_api_keys"])
        self.video = self.video_for(avatar=None)
        self.scene = scene.make(video=self.video)
        self.voice = voice_model.make(created_by=self.user, type="CUSTOM_API")

    def test_old_web_model_can_insert_after_the_operation_migration(self):
        old_apps = (
            MigrationExecutor(connection)
            .loader.project_state([("videomanagement", "0056_icon_owner")])
            .apps
        )
        old_video = old_apps.get_model("videomanagement", "Video")
        legacy = old_video.objects.create(
            title="Legacy web insert",
            created_by_id=self.user.pk,
            prompt_id=self.video.prompt_id,
            status="READY",
        )
        current = Video.objects.get(pk=legacy.pk)
        self.assertEqual(current.narration_retry_status, "")
        self.assertIsNone(current.operation_id)

    def queue_narration(self):
        with patch.object(regenerate_narration_task, "delay") as queue:
            response = self.client.patch(
                reverse("video-detail", args=[self.video.pk]),
                {"voice_id": str(self.voice.pk)},
            )
        self.assertEqual(response.status_code, 202, response.data)
        self.video.refresh_from_db()
        return queue.call_args

    @override_settings(VIDEO_TASK_STALE_AFTER=3600)
    def test_late_narration_cannot_take_over_a_visual_job_after_recovery(self):
        old = self.queue_narration()
        old_token = self.video.operation_id
        Video.objects.filter(pk=self.video.pk).update(
            updated_at=timezone.now() - timedelta(hours=2)
        )
        self.assertEqual(reap_stalled_videos(), 1)
        queue_scene_job(self.scene, generate_scene_image_task, "A new visual")
        self.video.refresh_from_db()
        current_token = self.video.operation_id
        self.assertNotEqual(old_token, current_token)
        with patch(
            "apps.videomanagement.tasks.regenerate_scene_narration"
        ) as narration:
            regenerate_narration_task.run(*old.args, **old.kwargs)
        narration.assert_not_called()
        self.assertEqual(_refresh_heartbeat(self.video.pk, old_token), 0)
        restore_video(self.video.pk, "READY", old_token)
        _mark_failed(self.video.pk, operation_id=old_token)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "GENERATION")
        self.assertEqual(self.video.operation_id, current_token)
        with patch("apps.videomanagement.tasks.scenes.generate_new_image") as visual:
            self.run_scene_job()
        visual.assert_called_once()

    def test_legacy_task_without_token_cannot_use_a_new_claim(self):
        self.queue_narration()
        with patch(
            "apps.videomanagement.tasks.regenerate_scene_narration"
        ) as narration:
            regenerate_narration_task.run(str(self.video.pk), "READY")
        narration.assert_not_called()
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "GENERATION")

    def test_a_superseded_worker_cannot_restore_status_or_mark_a_new_job_failed(self):
        for fail in (False, True):
            with self.subTest(fail=fail):
                self.video.status = "READY"
                self.video.voice_model = None
                self.video.save(update_fields=["status", "voice_model"])
                queued = self.queue_narration()
                replacement = uuid4()

                def supersede(_scene):
                    Video.objects.filter(pk=self.video.pk).update(
                        operation_id=replacement
                    )
                    if fail:
                        raise RuntimeError("Old provider failed")

                with patch(
                    "apps.videomanagement.tasks.regenerate_scene_narration",
                    side_effect=supersede,
                ):
                    if fail:
                        with self.assertRaises(RuntimeError):
                            regenerate_narration_task.run(*queued.args, **queued.kwargs)
                    else:
                        regenerate_narration_task.run(*queued.args, **queued.kwargs)
                self.video.refresh_from_db()
                self.assertEqual(self.video.operation_id, replacement)
                self.assertEqual(self.video.status, "GENERATION")

    @override_settings(VIDEO_TASK_STALE_AFTER=3600)
    def test_recovered_narration_exposes_an_explicit_retry_and_renews_its_token(self):
        old = self.queue_narration()
        old_token = self.video.operation_id
        Video.objects.filter(pk=self.video.pk).update(
            updated_at=timezone.now() - timedelta(hours=2)
        )
        self.assertEqual(reap_stalled_videos(), 1)
        response = self.client.get(reverse("video-detail", args=[self.video.pk]))
        self.assertTrue(response.data["can_retry_narration"])
        with patch.object(regenerate_narration_task, "delay") as queue:
            response = self.client.patch(
                reverse("video-detail", args=[self.video.pk]), {"retry_narration": True}
            )
        self.assertEqual(response.status_code, 202)
        self.video.refresh_from_db()
        self.assertNotEqual(self.video.operation_id, old_token)
        with patch(
            "apps.videomanagement.tasks.regenerate_scene_narration"
        ) as narration:
            regenerate_narration_task.run(*old.args, **old.kwargs)
            narration.assert_not_called()
            regenerate_narration_task.run(
                *queue.call_args.args, **queue.call_args.kwargs
            )
        narration.assert_called_once()
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "READY")
        self.assertEqual(self.video.narration_retry_status, "")
