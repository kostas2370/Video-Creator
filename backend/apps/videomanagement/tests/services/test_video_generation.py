"""Generation, with the model, TTS and imagery all stubbed."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.exceptions import APIException

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import (
    avatar,
    video,
    voice_model,
)
from ...services import (
    VideoGenerationServices,
)
from ...services.VideoGenerationServices import (
    create_pending_video,
    generate_video,
    resume_video,
)


A_SCRIPT = {
    "title": "Cats and how they nap",
    "scenes": [
        {
            "scene": "one",
            "sentences": [{"sentence": "hello", "image_description": "a cat"}],
        }
    ],
}


class CreatePendingVideoTests(TestCase):
    """The only part of generation cheap enough to run inside a request."""

    def setUp(self):
        self.user = user.make()

    def test_hands_back_a_video_the_client_can_poll_immediately(self):
        video = create_pending_video("make me a video", created_by=self.user)

        self.assertEqual(video.status, "GENERATION")
        self.assertIsNone(video.gpt_answer)
        self.assertEqual(video.created_by, self.user)

    def test_stores_the_message_as_the_prompt(self):
        video = create_pending_video("make me a video", created_by=self.user)

        self.assertEqual(video.prompt.prompt, "make me a video")

    def test_trims_a_long_message_to_fit_the_title(self):
        video = create_pending_video("x" * 200, created_by=self.user)

        self.assertEqual(len(video.title), 50)

    def test_prefers_an_explicit_title(self):
        video = create_pending_video(
            "clips", created_by=self.user, video_type="TWITCH", title="Fortnite 2026"
        )

        self.assertEqual(video.title, "Fortnite 2026")
        self.assertEqual(video.video_type, "TWITCH")


class GenerateVideoTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.voice = voice_model.make()
        self.video = create_pending_video("cats", created_by=self.user)

        for name, value in (
            ("get_reply", A_SCRIPT),
            ("generate_directory", "media/videos/cats"),
            ("make_scenes_speech", None),
            ("create_image_scenes", None),
            ("download_music", None),
            ("charge_user", 0.12),
        ):
            patcher = patch.object(VideoGenerationServices, name, return_value=value)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def generate(self, **kwargs):
        params = dict(
            genre="",
            message="cats",
            gpt_model="gpt-4",
            image_mode="WEB",
            avatar_selection="",
            style="vivid",
            target_audience="",
            voice_id=self.voice.id,
        )
        params.update(kwargs)
        return generate_video(video=self.video, **params)

    def test_uses_the_voice_that_was_chosen(self):
        chosen = voice_model.make(name="nova")

        video = self.generate(avatar_selection="", voice_id=chosen.id)

        self.assertEqual(video.voice_model, chosen)

    def test_picks_a_voice_when_none_was_chosen(self):
        video = self.generate(avatar_selection="", voice_id="")

        self.assertIsNotNone(video.voice_model)

    def test_a_blank_avatar_does_not_send_generation_looking_for_one(self):
        video = self.generate(avatar_selection="", voice_id=self.voice.id)

        self.assertIsNone(video.avatar)
        self.assertEqual(video.voice_model, self.voice)

    def test_fills_the_video_in_and_leaves_it_ready(self):
        video = self.generate()

        self.assertEqual(video.status, "READY")
        self.assertEqual(video.title, "Cats and how they nap")
        self.assertEqual(video.gpt_answer, A_SCRIPT)
        self.assertEqual(video.dir_name, "media/videos/cats")

    def test_records_the_choices_the_render_will_need(self):
        video = self.generate(
            subtitles=True, narration=False, avatar_position="left,top"
        )

        self.assertEqual(
            video.settings,
            dict(
                subtitles=True,
                narration=False,
                avatar_position="left,top",
                style="vivid",
                provider=None,
            ),
        )

    def test_asks_for_a_still_brief_for_an_image_provider(self):
        self.generate(provider="DALL-E")

        self.assertNotIn("camera move", self.get_reply.call_args.args[0])

    def test_asks_for_a_shot_brief_for_a_video_provider(self):
        # A still model wastes most of its value on "a tray of donuts", and the other
        # way round.
        self.generate(provider="sora")

        self.assertIn("camera move", self.get_reply.call_args.args[0])

    def test_narrates_before_generating_the_visuals(self):
        # create_image_scene reads the narration length off disk to size a clip, so
        # the order matters.
        calls = []
        self.make_scenes_speech.side_effect = lambda *a, **k: calls.append("speech")
        self.create_image_scenes.side_effect = lambda *a, **k: calls.append("images")

        self.generate()

        self.assertEqual(calls, ["speech", "images"])

    def test_uses_the_avatars_own_voice_when_an_avatar_was_picked(self):
        picked = avatar.make()

        video = self.generate(avatar_selection=str(picked.id))

        self.assertEqual(video.avatar, picked)
        self.assertEqual(video.voice_model, picked.voice)

    def test_skips_the_visuals_entirely_when_no_image_mode_was_asked_for(self):
        self.generate(image_mode=False)

        self.create_image_scenes.assert_not_called()

    def test_charges_the_owner_once_the_video_is_ready(self):
        video = self.generate()

        self.charge_user.assert_called_once_with(
            self.user, "generation_limit_for_ai", video
        )

    def test_carries_on_when_the_music_cannot_be_downloaded(self):
        self.download_music.side_effect = RuntimeError("video unavailable")

        self.assertEqual(self.generate().status, "READY")


class ResumeGenerationTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.video = video.make(
            created_by=self.user,
            status="FAILED",
            mode="WEB",
            gpt_answer=A_SCRIPT,
            dir_name="media/videos/cats",
            settings=dict(narration=True, style="vivid", provider="bing"),
        )

        for name in ("make_scenes_speech", "create_image_scenes"):
            patcher = patch.object(VideoGenerationServices, name)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_carries_on_from_the_script_it_already_has(self):
        with patch.object(VideoGenerationServices, "get_reply") as asked:
            resumed = resume_video(self.video)

        asked.assert_not_called()
        self.assertEqual(resumed.gpt_answer, A_SCRIPT)
        self.assertEqual(resumed.status, "READY")

    def test_fills_in_the_narration_and_the_visuals_again(self):
        resume_video(self.video)

        self.make_scenes_speech.assert_called_once()
        self.create_image_scenes.assert_called_once()

    def test_asks_the_provider_the_first_run_chose(self):
        resume_video(self.video)

        self.assertEqual(self.create_image_scenes.call_args.kwargs["provider"], "bing")
        self.assertEqual(self.create_image_scenes.call_args.kwargs["style"], "vivid")

    def test_leaves_the_visuals_alone_for_a_video_that_asked_for_none(self):
        self.video.mode = None
        self.video.save()

        resume_video(self.video)

        self.create_image_scenes.assert_not_called()

    def test_refuses_a_video_that_never_got_a_script(self):
        self.video.gpt_answer = None
        self.video.save()

        with self.assertRaises(APIException):
            resume_video(self.video)
