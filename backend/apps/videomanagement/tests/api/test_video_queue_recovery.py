from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone

from ...models import Video, VideoStatus
from .base import ApiTestCase


class VideoQueueRecoveryTests(ApiTestCase):
    def test_render_dispatch_failure_restores_status_and_allows_retry(self):
        for previous in (VideoStatus.READY, VideoStatus.COMPLETED):
            with self.subTest(previous=previous):
                video = self.video_for(status=previous, output="media/existing.mp4")
                endpoint = reverse("video-render-video", args=[video.pk])
                with patch(
                    "apps.videomanagement.tasks.render_video_task.delay",
                    side_effect=RuntimeError("offline"),
                ):
                    response = self.client.patch(endpoint)
                self.assertEqual(response.status_code, 503, response.data)
                video.refresh_from_db()
                self.assertEqual(video.status, previous)
                self.assertEqual(video.output.name, "media/existing.mp4")
                with patch(
                    "apps.videomanagement.tasks.render_video_task.delay"
                ) as queue:
                    retry = self.client.patch(endpoint)
                self.assertEqual(retry.status_code, 202, retry.data)
                queue.assert_called_once_with(video_id=video.pk)

    def test_resume_dispatch_failure_restores_status_and_allows_retry(self):
        for previous in (VideoStatus.FAILED, VideoStatus.READY):
            with self.subTest(previous=previous):
                video = self.video_for(
                    status=previous,
                    gpt_answer={"title": "Saved", "scenes": []},
                    dir_name="media/saved",
                )
                endpoint = reverse("video-resume", args=[video.pk])
                with patch(
                    "apps.videomanagement.tasks.resume_video_task.delay",
                    side_effect=RuntimeError("offline"),
                ):
                    response = self.client.patch(endpoint)
                self.assertEqual(response.status_code, 503, response.data)
                video.refresh_from_db()
                self.assertEqual(video.status, previous)
                self.assertEqual(video.gpt_answer["title"], "Saved")
                with patch("apps.videomanagement.tasks.resume_video_task.delay"):
                    retry = self.client.patch(endpoint)
                self.assertEqual(retry.status_code, 202, retry.data)

    def test_failed_dispatch_does_not_overwrite_a_later_worker_update(self):
        video = self.video_for(status=VideoStatus.READY)

        def dispatched_then_failed(**kwargs):
            Video.objects.filter(pk=video.pk).update(
                status=VideoStatus.FAILED, updated_at=timezone.now()
            )
            raise RuntimeError("acknowledgement lost")

        with patch(
            "apps.videomanagement.tasks.render_video_task.delay",
            side_effect=dispatched_then_failed,
        ):
            response = self.client.patch(reverse("video-render-video", args=[video.pk]))
        self.assertEqual(response.status_code, 503)
        video.refresh_from_db()
        self.assertEqual(video.status, VideoStatus.FAILED)

    def test_claim_refreshes_the_stalled_job_timestamp(self):
        video = self.video_for(status=VideoStatus.READY)
        old = timezone.now() - timedelta(days=1)
        Video.objects.filter(pk=video.pk).update(updated_at=old)
        with patch("apps.videomanagement.tasks.render_video_task.delay"):
            response = self.client.patch(reverse("video-render-video", args=[video.pk]))
        self.assertEqual(response.status_code, 202, response.data)
        video.refresh_from_db()
        self.assertGreater(video.updated_at, old)
