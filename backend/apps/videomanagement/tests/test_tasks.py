"""The worker jobs. Each one owns a video and must leave it in a terminal status."""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from ..baker_recipes import video
from ..models import Video
from ..tasks import (
    generate_twitch_video_task,
    generate_video_task,
    reap_stalled_videos,
    regenerate_video_task,
    render_video_task,
)


class TaskFailureTests(TestCase):
    def setUp(self):
        self.video = video.make(status="GENERATION")

    def test_generation_leaves_the_video_failed_and_re_raises(self):
        with patch(
            "apps.videomanagement.services.VideoGenerationServices.generate_video",
            side_effect=RuntimeError("the model refused"),
        ):
            with self.assertRaises(RuntimeError):
                generate_video_task(video_id=self.video.id)

        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")

    def test_twitch_generation_leaves_the_video_failed_and_re_raises(self):
        with patch(
            "apps.videomanagement.services.TwitchGenerationService.generate_twitch_video",
            side_effect=RuntimeError("twitch is down"),
        ):
            with self.assertRaises(RuntimeError):
                generate_twitch_video_task(video_id=self.video.id)

        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")

    def test_rendering_leaves_the_video_failed_and_re_raises(self):
        with patch(
            "apps.videomanagement.utils.video_utils.make_video",
            side_effect=RuntimeError("the encoder died"),
        ):
            with self.assertRaises(RuntimeError):
                render_video_task(video_id=self.video.id)

        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")

    def test_regeneration_leaves_the_video_failed_and_re_raises(self):
        with patch(
            "apps.videomanagement.services.VideoServices.video_regenerate",
            side_effect=RuntimeError("no voice"),
        ):
            with self.assertRaises(RuntimeError):
                regenerate_video_task(video_id=self.video.id)

        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")


class TaskSuccessTests(TestCase):
    def setUp(self):
        self.video = video.make(status="GENERATION")

    def test_generation_hands_its_parameters_to_the_service(self):
        with patch(
            "apps.videomanagement.services.VideoGenerationServices.generate_video"
        ) as generate:
            returned = generate_video_task(video_id=self.video.id, message="cats")

        self.assertEqual(returned, self.video.id)
        self.assertEqual(generate.call_args.kwargs["message"], "cats")
        self.assertEqual(generate.call_args.kwargs["video"].pk, self.video.pk)

    def test_rendering_hands_the_video_to_make_video(self):
        with patch("apps.videomanagement.utils.video_utils.make_video") as render:
            self.assertEqual(render_video_task(video_id=self.video.id), self.video.id)

        self.assertEqual(render.call_args.args[0].pk, self.video.pk)


class ReapStalledVideosTests(TestCase):
    """A task killed without unwinding never reaches its own except clause."""

    def stale(self, status, age_seconds):
        stalled = video.make(status=status)
        # updated_at is auto_now, so it has to be written past the ORM.
        Video.objects.filter(pk=stalled.pk).update(
            updated_at=timezone.now() - timedelta(seconds=age_seconds)
        )
        return stalled

    @override_settings(VIDEO_TASK_STALE_AFTER=3600)
    def test_fails_a_video_no_worker_can_still_be_holding(self):
        video = self.stale("RENDERING", 7200)

        self.assertEqual(reap_stalled_videos(), 1)
        video.refresh_from_db()
        self.assertEqual(video.status, "FAILED")

    @override_settings(VIDEO_TASK_STALE_AFTER=3600)
    def test_leaves_a_video_a_worker_is_still_on(self):
        video = self.stale("GENERATION", 60)

        self.assertEqual(reap_stalled_videos(), 0)
        video.refresh_from_db()
        self.assertEqual(video.status, "GENERATION")

    @override_settings(VIDEO_TASK_STALE_AFTER=3600)
    def test_leaves_videos_that_already_reached_an_answer(self):
        for status in ("READY", "COMPLETED", "FAILED"):
            with self.subTest(status=status):
                video = self.stale(status, 7200)

                reap_stalled_videos()

                video.refresh_from_db()
                self.assertEqual(video.status, status)
