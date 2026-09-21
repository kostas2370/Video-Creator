"""The service layer, with generation, TTS and Twitch all stubbed."""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.exceptions import APIException, ValidationError

from apps.usermanagement.baker_recipes import user

from ..baker_recipes import (
    avatar,
    intro,
    outro,
    scene,
    scene_image,
    twitch_video,
    video,
    voice_model,
)
from ..models import SceneImage
from ..services import (
    SceneServices,
    TwitchGenerationService,
    VideoGenerationServices,
    VideoServices,
)
from ..services.SceneServices import create_scene, generate_scene, update_scene
from ..services.TwitchGenerationService import generate_twitch_video, twitch_video_title
from ..services.VideoGenerationServices import create_pending_video, generate_video
from ..services.VideoServices import video_regenerate, video_update

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
            dict(subtitles=True, narration=False, avatar_position="left,top"),
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


class GenerateSceneTests(TestCase):
    def test_asks_the_model_for_a_rewrite(self):
        line = scene.make(text="the old line")

        with patch.object(
            SceneServices, "get_update_sentence", return_value="a new line"
        ) as rewrite:
            self.assertEqual(generate_scene("make it funnier", line), "a new line")

        self.assertIn("the old line", rewrite.call_args.args[0])

    def test_does_not_call_the_model_when_the_text_is_unchanged(self):
        line = scene.make(text=" the old line ")

        with patch.object(SceneServices, "get_update_sentence") as rewrite:
            self.assertEqual(generate_scene("the old line", line), "the old line")

        rewrite.assert_not_called()


class UpdateSceneServiceTests(TestCase):
    def test_stores_the_new_text_and_resynthesises_the_line(self):
        line = scene.make(text="the old line")

        with patch.object(SceneServices, "update") as resynthesise:
            self.assertEqual(update_scene("a new line", line), "a new line")

        resynthesise.assert_called_once_with(line)

    def test_keeps_the_old_text_when_the_new_one_is_blank(self):
        line = scene.make(text="the old line")

        with patch.object(SceneServices, "update"):
            self.assertEqual(update_scene("", line), "the old line")


class CreateSceneTests(TestCase):
    def setUp(self):
        self.video = video.make()

    def test_adds_a_narrated_scene_to_an_ai_video(self):
        line = scene.prepare(text="a new line")

        with patch.object(
            SceneServices, "make_scene_speech", return_value=line
        ) as speech:
            created = create_scene(
                self.video, {"text": "a new line", "is_last": True}, files={}
            )

        self.assertIs(created, line)
        self.assertEqual(speech.call_args.args[3], "a new line")

    def test_attaches_an_uploaded_image_to_the_new_scene(self):
        line = scene.make(prompt=self.video.prompt)

        with patch.object(SceneServices, "make_scene_speech", return_value=line):
            create_scene(
                self.video,
                {"text": "a new line", "with_audio": True},
                files={"image": "media/images/uploaded.png"},
            )

        image = SceneImage.objects.get(scene=line)
        self.assertEqual(image.file, "media/images/uploaded.png")
        self.assertTrue(image.with_audio)

    def test_generates_an_image_when_one_was_described_instead(self):
        line = scene.make(prompt=self.video.prompt)

        with (
            patch.object(SceneServices, "make_scene_speech", return_value=line),
            patch.object(SceneServices, "create_image_scene") as generate,
        ):
            create_scene(
                self.video,
                {"text": "a new line", "image_description": "a cat"},
                files={},
            )

        self.assertEqual(generate.call_args.kwargs["image"], "a cat")

    def test_rejects_an_ai_scene_with_no_text(self):
        with self.assertRaises(ValidationError):
            create_scene(self.video, {"is_last": False}, files={})

    def test_adds_a_clip_to_a_twitch_video(self):
        video = twitch_video.make()
        client = MagicMock()
        client.get_clip_by_url.return_value = [{"title": "a clip"}]
        client.download_clip.return_value = "clips/raw.mp4"

        with (
            patch.object(SceneServices, "TwitchClient", return_value=client),
            patch.object(SceneServices, "create_twitch_clip_scene") as create,
        ):
            create_scene(video, {"url": "https://clips.twitch.tv/abc"}, files={})

        create.assert_called_once_with("clips/raw.mp4", "a clip", video.prompt)

    def test_rejects_a_twitch_scene_with_no_url(self):
        video = twitch_video.make()

        with self.assertRaises(ValidationError):
            create_scene(video, {"text": "a line"}, files={})

    def test_reports_a_twitch_clip_that_cannot_be_fetched(self):
        video = twitch_video.make()
        client = MagicMock()
        client.get_clip_by_url.side_effect = RuntimeError("gone")

        with patch.object(SceneServices, "TwitchClient", return_value=client):
            with self.assertRaises(APIException):
                create_scene(video, {"url": "https://clips.twitch.tv/abc"}, files={})


class VideoUpdateTests(TestCase):
    def setUp(self):
        self.video = video.make()

    def test_renames_the_video(self):
        updated = video_update(self.video, title="A New Name", avatar=None)

        self.assertEqual(updated.title, "A New Name")

    def test_records_the_subtitle_and_avatar_choices(self):
        updated = video_update(
            self.video,
            title="t",
            avatar=None,
            subtitles=True,
            avatar_position="left,top",
        )

        self.assertEqual(
            updated.settings, dict(subtitles=True, avatar_position="left,top")
        )

    def test_clears_the_avatar_when_none_was_chosen(self):
        self.video.avatar = avatar.make()

        for choice in (None, "", "None"):
            with self.subTest(choice=choice):
                self.assertIsNone(
                    video_update(self.video, title="t", avatar=choice).avatar
                )

    def test_re_records_every_line_when_the_avatar_brings_a_new_voice(self):
        picked = avatar.make()
        scene.make(prompt=self.video.prompt, _quantity=2)

        with patch.object(VideoServices, "update_scene") as resynthesise:
            updated = video_update(self.video, title="t", avatar=str(picked.id))

        self.assertEqual(updated.voice_model, picked.voice)
        self.assertEqual(resynthesise.call_count, 2)

    def test_leaves_the_recordings_alone_when_the_voice_is_unchanged(self):
        picked = avatar.make(voice=self.video.voice_model)

        with patch.object(VideoServices, "update_scene") as resynthesise:
            video_update(self.video, title="t", avatar=str(picked.id))

        resynthesise.assert_not_called()

    def test_never_gives_a_twitch_video_an_avatar(self):
        clips = twitch_video.make()
        picked = avatar.make()

        self.assertIsNone(video_update(clips, title="t", avatar=str(picked.id)).avatar)

    def test_attaches_the_intro_and_outro_that_were_chosen(self):
        opening = intro.make()
        closing = outro.make()

        updated = video_update(
            self.video,
            title="t",
            avatar=None,
            intro=str(opening.id),
            outro=str(closing.id),
        )

        self.assertEqual(updated.intro, opening)
        self.assertEqual(updated.outro, closing)

    def test_reports_an_intro_that_does_not_exist(self):
        with self.assertRaises(APIException):
            video_update(self.video, title="t", avatar=None, intro="99999")

    def test_reports_an_outro_that_does_not_exist(self):
        with self.assertRaises(APIException):
            video_update(self.video, title="t", avatar=None, outro="99999")


class VideoRegenerateTests(TestCase):
    def test_re_records_every_line_and_regenerates_every_image(self):
        completed = video.make(status="COMPLETED")
        scenes = scene.make(prompt=completed.prompt, _quantity=2)
        for line in scenes:
            scene_image.make(scene=line)

        with (
            patch.object(VideoServices, "update_scene") as resynthesise,
            patch.object(VideoServices, "generate_new_image") as regenerate,
        ):
            video_regenerate(completed)

        self.assertEqual(resynthesise.call_count, 2)
        self.assertEqual(regenerate.call_count, 2)
        completed.refresh_from_db()
        self.assertEqual(completed.status, "READY")


class TwitchGenerationTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.video = create_pending_video(
            "clips", created_by=self.user, video_type="TWITCH", title="Fortnite"
        )
        self.client = MagicMock()
        self.client.get_game_id.return_value = "33214"
        self.client.get_streamer_id.return_value = "1234"
        self.client.get_clips.return_value = [
            {"title": f"clip {n}", "url": f"https://clips.twitch.tv/{n}"}
            for n in range(3)
        ]
        self.client.download_clip.side_effect = (
            lambda clip: f"clips/{clip['title']}.mp4"
        )

        for name, value in (
            ("TwitchClient", self.client),
            ("generate_directory", "media/videos/fortnite"),
            ("create_twitch_clip_scene", None),
            ("charge_user", 0.05),
        ):
            patcher = patch.object(TwitchGenerationService, name, return_value=value)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_titles_the_video_with_the_day_it_was_made(self):
        self.assertTrue(twitch_video_title("Fortnite").startswith("Fortnite "))

    def test_collects_the_clips_and_leaves_the_video_ready(self):
        video = generate_twitch_video(self.video, mode="game", value="Fortnite")

        self.assertEqual(video.status, "READY")
        self.assertEqual(self.create_twitch_clip_scene.call_count, 3)

    def test_looks_a_game_up_by_name(self):
        generate_twitch_video(self.video, mode="game", value="Fortnite")

        self.client.get_game_id.assert_called_once_with("Fortnite")
        self.client.get_streamer_id.assert_not_called()

    def test_looks_a_streamer_up_by_name(self):
        generate_twitch_video(self.video, mode="streamer", value="someone")

        self.client.get_streamer_id.assert_called_once_with("someone")

    def test_takes_no_more_clips_than_were_asked_for(self):
        generate_twitch_video(self.video, mode="game", value="Fortnite", amt=2)

        self.assertEqual(self.create_twitch_clip_scene.call_count, 2)

    def test_credits_every_clip_it_used(self):
        video = generate_twitch_video(self.video, mode="game", value="Fortnite")

        self.assertIn("https://clips.twitch.tv/0", video.gpt_answer)
        self.assertIn("clip 2", video.gpt_answer)

    def test_skips_a_clip_that_would_not_download(self):
        self.client.download_clip.side_effect = [None, "clips/b.mp4", None]

        video = generate_twitch_video(self.video, mode="game", value="Fortnite")

        self.assertEqual(self.create_twitch_clip_scene.call_count, 1)
        self.assertEqual(video.status, "READY")

    def test_charges_the_owner_against_their_twitch_balance(self):
        video = generate_twitch_video(self.video, mode="game", value="Fortnite")

        self.charge_user.assert_called_once_with(
            self.user, "generation_limit_for_twitch", video
        )
