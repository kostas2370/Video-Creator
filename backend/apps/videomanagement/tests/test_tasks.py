"""The worker jobs. Each one owns a video and must leave it in a terminal status."""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.apikeysmanagement.models import Provider
from apps.usermanagement.baker_recipes import user

from ..baker_recipes import video
from ..models import Video, VoiceModel
from ..utils import tts_utils
from ..tasks import (
    generate_twitch_video_task,
    import_user_voices,
    resume_video_task,
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
            "apps.videomanagement.utils.composer.render.make_video",
            side_effect=RuntimeError("the encoder died"),
        ):
            with self.assertRaises(RuntimeError):
                render_video_task(video_id=self.video.id)

        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")

    def test_resuming_leaves_the_video_failed_and_re_raises(self):
        with patch(
            "apps.videomanagement.services.VideoGenerationServices.resume_video",
            side_effect=RuntimeError("the provider is still down"),
        ):
            with self.assertRaises(RuntimeError):
                resume_video_task(video_id=self.video.id)

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
        with patch("apps.videomanagement.utils.composer.render.make_video") as render:
            self.assertEqual(render_video_task(video_id=self.video.id), self.video.id)

        self.assertEqual(render.call_args.args[0].pk, self.video.pk)

    def test_resuming_hands_the_video_to_the_service(self):
        with patch(
            "apps.videomanagement.services.VideoGenerationServices.resume_video"
        ) as resume:
            returned = resume_video_task(video_id=self.video.id)

        self.assertEqual(returned, self.video.id)
        self.assertEqual(resume.call_args.args[0].pk, self.video.pk)

    def test_twitch_generation_hands_its_parameters_to_the_service(self):
        with patch(
            "apps.videomanagement.services.TwitchGenerationService.generate_twitch_video"
        ) as generate:
            returned = generate_twitch_video_task(
                video_id=self.video.id, channel="a streamer"
            )

        self.assertEqual(returned, self.video.id)
        self.assertEqual(generate.call_args.kwargs["channel"], "a streamer")
        self.assertEqual(generate.call_args.kwargs["video"].pk, self.video.pk)

    def test_regeneration_hands_the_video_to_the_service(self):
        with patch(
            "apps.videomanagement.services.VideoServices.video_regenerate"
        ) as regenerate:
            returned = regenerate_video_task(video_id=self.video.id)

        self.assertEqual(returned, self.video.id)
        self.assertEqual(regenerate.call_args.args[0].pk, self.video.pk)


class ImportUserVoicesTests(TestCase):
    def setUp(self):
        self.user = user.make()

    def labs_returns(self, *voices):
        return patch(
            "apps.videomanagement.utils.tts_utils.get_voices_from_labs",
            return_value=list(voices),
        )

    def test_imports_the_voices_against_the_user_who_owns_the_key(self):
        with self.labs_returns(
            {"name": "Rachel", "voice_id": "abc", "preview_url": "https://a.test/x"}
        ):
            added = import_user_voices(self.user.id, Provider.ELEVENLABS)

        voice = VoiceModel.objects.get(path="abc")
        self.assertEqual(added, 1)
        self.assertEqual(voice.created_by, self.user)
        self.assertEqual(voice.provider, "eleven_labs")
        self.assertEqual(voice.type, "API")

    def test_running_it_twice_does_not_duplicate_anything(self):
        voices = [{"name": "Rachel", "voice_id": "abc", "preview_url": ""}]

        with self.labs_returns(*voices):
            import_user_voices(self.user.id, Provider.ELEVENLABS)
            added = import_user_voices(self.user.id, Provider.ELEVENLABS)

        self.assertEqual(added, 0)
        self.assertEqual(VoiceModel.objects.filter(path="abc").count(), 1)

    def test_two_users_can_hold_a_voice_of_the_same_name(self):
        stranger = user.make()
        voices = [{"name": "Rachel", "voice_id": "abc", "preview_url": ""}]

        with self.labs_returns(*voices):
            import_user_voices(self.user.id, Provider.ELEVENLABS)
            import_user_voices(stranger.id, Provider.ELEVENLABS)

        self.assertEqual(VoiceModel.objects.filter(name="Rachel").count(), 2)

    def test_does_nothing_for_a_user_who_no_longer_exists(self):
        self.assertEqual(import_user_voices(999999, Provider.ELEVENLABS), 0)

    def test_a_provider_that_will_not_answer_fails_the_import(self):
        owner = user.make()

        with patch.object(
            tts_utils, "get_voices_from_labs", side_effect=RuntimeError("401")
        ):
            with self.assertRaises(RuntimeError):
                import_user_voices(owner.id, Provider.ELEVENLABS)

        self.assertEqual(VoiceModel.objects.count(), 0)


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
