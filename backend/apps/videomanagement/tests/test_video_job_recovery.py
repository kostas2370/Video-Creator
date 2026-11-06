from datetime import timedelta
from threading import Event, Thread
from unittest.mock import Mock, patch

from django.db import connections, transaction
from django.test import (
    TestCase,
    TransactionTestCase,
    override_settings,
    skipUnlessDBFeature,
)
from django.utils import timezone

from apps.videomanagement.baker_recipes import video
from apps.videomanagement.models import Video
from apps.videomanagement.services.videos import recovery
from apps.videomanagement.tasks import (
    create_scene_task,
    generate_video_task,
    reap_stalled_videos,
    regenerate_narration_task,
    render_video_task,
    resume_video_task,
)


@override_settings(VIDEO_TASK_STALE_AFTER=3600)
class VideoJobRecoveryTests(TestCase):
    def setUp(self):
        self.video = video.make(status="GENERATION")
        Video.objects.filter(pk=self.video.pk).update(
            updated_at=timezone.now() - timedelta(hours=2)
        )

    def test_a_running_jobs_heartbeat_prevents_recovery_without_editor_events(self):
        with patch("apps.videomanagement.signals.publish_update") as notify:
            with recovery.video_job_heartbeat(self.video.pk) as active:
                self.assertTrue(active)
                self.assertEqual(reap_stalled_videos(), 0)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "GENERATION")
        notify.assert_not_called()

    def test_rechecks_projects_that_finish_or_restart_during_the_sweep(self):
        queryset_class = type(Video.objects.all())
        lock = queryset_class.select_for_update
        for status in ("COMPLETED", "GENERATION"):
            with self.subTest(status=status):
                Video.objects.filter(pk=self.video.pk).update(
                    status="GENERATION", updated_at=timezone.now() - timedelta(hours=2)
                )

                def advance(queryset, *args, **kwargs):
                    Video.objects.filter(pk=self.video.pk).update(
                        status=status, updated_at=timezone.now()
                    )
                    return lock(queryset, *args, **kwargs)

                with patch.object(queryset_class, "select_for_update", advance):
                    self.assertEqual(reap_stalled_videos(), 0)
                self.video.refresh_from_db()
                self.assertEqual(self.video.status, status)

    def test_recovered_projects_notify_the_editor_and_keep_saved_media(self):
        self.video.render_error = {"saved": "metadata"}
        self.video.save(update_fields=["render_error"])
        Video.objects.filter(pk=self.video.pk).update(
            updated_at=timezone.now() - timedelta(hours=2)
        )
        original = self.video.gpt_answer, self.video.voice_model_id, self.video.dir_name
        with patch("apps.videomanagement.signals.publish_update") as notify:
            self.assertEqual(reap_stalled_videos(), 1)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")
        self.assertEqual(
            (self.video.gpt_answer, self.video.voice_model_id, self.video.dir_name),
            original,
        )
        notify.assert_called_once()
        self.assertEqual(reap_stalled_videos(), 0)

    def test_late_tasks_do_not_restart_a_recovered_project(self):
        self.assertEqual(reap_stalled_videos(), 1)
        with (
            patch(
                "apps.videomanagement.tasks.video_generation.generate_video"
            ) as generate,
            patch("apps.videomanagement.tasks.video_generation.resume_video") as resume,
            patch("apps.videomanagement.tasks.render.make_video") as render,
            patch("apps.videomanagement.tasks.regenerate_scene_narration") as narrate,
            patch("apps.videomanagement.tasks.scene_generation.create_scene") as create,
            patch("apps.videomanagement.tasks.default_storage.delete") as cleanup,
        ):
            generate_video_task(video_id=self.video.pk)
            resume_video_task(video_id=self.video.pk)
            render_video_task(video_id=self.video.pk)
            regenerate_narration_task(self.video.pk, "READY")
            create_scene_task(self.video.pk, {"text": "Late"}, "media/staged.png")
        for provider in (generate, resume, render, narrate, create):
            provider.assert_not_called()
        cleanup.assert_called_once_with("media/staged.png")
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")

    def test_a_heartbeat_thread_retries_database_errors_and_closes_its_connection(self):
        stopped = Mock()
        stopped.wait.side_effect = [False, False, True]
        with (
            patch.object(
                recovery,
                "_refresh_heartbeat",
                side_effect=[RuntimeError("temporary outage"), True],
            ) as refresh,
            patch.object(recovery, "close_old_connections"),
            patch.object(recovery.connections, "close_all") as close,
            patch.object(recovery.logger, "exception"),
        ):
            recovery._heartbeat(self.video.pk, stopped)
        self.assertEqual(refresh.call_count, 2)
        close.assert_called_once()

    def test_a_task_exception_stops_its_heartbeat(self):
        with (
            patch.object(recovery, "Thread") as thread,
            patch.object(recovery, "Event") as event,
        ):
            with self.assertRaisesRegex(RuntimeError, "provider stopped"):
                with recovery.video_job_heartbeat(self.video.pk):
                    raise RuntimeError("provider stopped")
        event.return_value.set.assert_called_once()
        thread.return_value.join.assert_called_once()


class LiveVideoHeartbeatTests(TransactionTestCase):
    def test_worker_thread_refreshes_liveness_on_its_own_database_connection(self):
        project = video.make(status="GENERATION")
        heartbeat = Event()
        refresh = recovery._refresh_heartbeat
        calls = []

        def record(video_id, operation_id=None):
            result = refresh(video_id, operation_id)
            calls.append(result)
            if len(calls) >= 2:
                heartbeat.set()
            return result

        with (
            patch.object(recovery, "HEARTBEAT_SECONDS", 0.01),
            patch.object(recovery, "_refresh_heartbeat", side_effect=record),
        ):
            with recovery.video_job_heartbeat(project.pk):
                self.assertTrue(
                    heartbeat.wait(timeout=5),
                    "Worker heartbeat never reached the database",
                )
        project.refresh_from_db()
        self.assertGreaterEqual(len(calls), 2)
        self.assertTrue(all(calls))
        self.assertEqual(project.status, "GENERATION")

    @override_settings(VIDEO_TASK_STALE_AFTER=3600)
    @skipUnlessDBFeature("has_select_for_update_skip_locked")
    def test_recovery_skips_a_project_locked_by_a_worker(self):
        project = video.make(status="GENERATION")
        Video.objects.filter(pk=project.pk).update(
            updated_at=timezone.now() - timedelta(hours=2)
        )
        locked, release, finished = Event(), Event(), Event()
        errors = []

        def hold_project():
            try:
                with transaction.atomic():
                    Video.objects.select_for_update().get(pk=project.pk)
                    locked.set()
                    release.wait(timeout=5)
            except Exception as exc:
                errors.append(exc)
            finally:
                connections.close_all()
                finished.set()

        worker = Thread(target=hold_project, daemon=True)
        worker.start()
        try:
            self.assertTrue(locked.wait(timeout=5))
            self.assertEqual(reap_stalled_videos(), 0)
            self.assertFalse(
                finished.is_set(), "Recovery waited for an active worker's lock"
            )
        finally:
            release.set()
            worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        project.refresh_from_db()
        self.assertEqual(project.status, "GENERATION")
