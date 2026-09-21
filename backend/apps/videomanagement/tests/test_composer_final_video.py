from unittest.mock import patch

from django.test import TestCase

from ..baker_recipes import avatar, background, intro, music, outro, video
from ..utils.composer import render
from ..utils.composer.render import handle_final_video
from .doubles import FakeAudio, FakeClip


class HandleFinalVideoTests(TestCase):
    def setUp(self):
        self.clip = FakeClip()
        self.audio = FakeAudio(duration=12.0)
        self.video = video.make(settings=dict(subtitles=False))

    def assemble(self, subtitles=None, backdrop=None, **patches):
        stubs = {
            "handle_background": self.clip,
            "handle_music": self.audio,
            "handle_avatar_video": self.clip,
        }
        stubs.update(patches)

        started = {}
        for name, value in stubs.items():
            patcher = patch.object(render, name, return_value=value)
            started[name] = patcher.start()
            self.addCleanup(patcher.stop)

        result = handle_final_video(
            backdrop, self.audio, self.clip, self.video, subtitles or []
        )

        return result, started

    def test_lays_the_background_under_the_narrations_length(self):
        _, stubs = self.assemble(backdrop=background.make())

        self.assertEqual(stubs["handle_background"].call_args.args[0], 12.0)

    def test_falls_back_to_the_videos_own_length_when_it_is_silent(self):
        self.audio = None

        _, stubs = self.assemble()

        self.assertEqual(stubs["handle_background"].call_args.args[0], 10.0)

    def test_mixes_music_in_only_when_the_video_has_some(self):
        _, without = self.assemble()
        without["handle_music"].assert_not_called()

    def test_mixes_music_in_when_the_video_has_some(self):
        self.video.music = music.make()

        _, stubs = self.assemble()

        stubs["handle_music"].assert_called_once()

    def test_puts_the_soundtrack_on_the_video(self):
        result, _ = self.assemble()

        self.assertIn("set_audio", result.effects)

    def test_leaves_a_silent_video_without_an_audio_track(self):
        self.audio = None

        result, _ = self.assemble()

        self.assertNotIn("set_audio", result.effects)

    def test_overlays_the_avatar_only_when_one_was_chosen(self):
        _, without = self.assemble()
        without["handle_avatar_video"].assert_not_called()

        self.video.avatar = avatar.make()
        _, with_avatar = self.assemble()
        with_avatar["handle_avatar_video"].assert_called_once()

    def test_burns_subtitles_in_when_they_were_asked_for(self):
        self.video.settings = dict(subtitles=True)
        subs = FakeClip()

        with (
            patch.object(render, "concatenate_videoclips", return_value=subs) as joined,
            patch.object(
                render, "CompositeVideoClip", return_value=self.clip
            ) as layered,
        ):
            self.assemble(subtitles=[subs])

        joined.assert_called_once()
        layered.assert_called_once()

    def test_ignores_subtitles_the_video_did_not_ask_for(self):
        self.video.settings = dict(subtitles=False)

        with patch.object(render, "CompositeVideoClip") as layered:
            self.assemble(subtitles=[FakeClip()])

        layered.assert_not_called()

    def test_ignores_a_subtitle_setting_with_no_subtitles_behind_it(self):
        self.video.settings = dict(subtitles=True)

        with patch.object(render, "CompositeVideoClip") as layered:
            self.assemble(subtitles=[])

        layered.assert_not_called()

    def test_puts_an_intro_in_front_and_an_outro_behind(self):
        self.video.intro = intro.make()
        self.video.outro = outro.make()

        with (
            patch.object(render, "VideoFileClip", return_value=FakeClip()),
            patch.object(
                render, "concatenate_videoclips", return_value=self.clip
            ) as joined,
        ):
            self.assemble()

        self.assertEqual(joined.call_count, 2)
        self.assertIs(joined.call_args_list[0].args[0][1], self.clip)
        self.assertIs(joined.call_args_list[1].args[0][0], self.clip)

    def test_adds_neither_when_the_video_has_no_intro_or_outro(self):
        with patch.object(render, "concatenate_videoclips") as joined:
            self.assemble()

        joined.assert_not_called()
