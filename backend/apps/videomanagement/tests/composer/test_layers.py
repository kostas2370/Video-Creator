from unittest.mock import patch

from django.test import SimpleTestCase

from ...baker_recipes import music, video
from ...utils.composer import layers
from ...utils.composer.layers import handle_music
from ..doubles import FakeAudio


class HandleMusicTests(SimpleTestCase):
    def setUp(self):
        self.video = video.prepare()
        self.video.music = music.prepare()

    def test_loops_music_that_is_shorter_than_the_video(self):
        music = FakeAudio(duration=10.0)

        with (
            patch.object(layers, "AudioFileClip", return_value=music),
            patch.object(
                layers, "concatenate_audioclips", return_value=music
            ) as concatenate,
            patch.object(layers, "CompositeAudioClip") as composite,
        ):
            handle_music(self.video, FakeAudio(25.0), duration=25.0)

        # 25s of video over a 10s track: three copies, then trimmed back to 25s.
        self.assertEqual(len(concatenate.call_args.args[0]), 3)
        composite.assert_called_once()

    def test_trims_music_that_is_longer_than_the_video(self):
        music = FakeAudio(duration=60.0)

        with (
            patch.object(layers, "AudioFileClip", return_value=music),
            patch.object(layers, "concatenate_audioclips") as concatenate,
            patch.object(layers, "CompositeAudioClip"),
        ):
            handle_music(self.video, FakeAudio(25.0), duration=25.0)

        concatenate.assert_not_called()
        self.assertIn("subclip", music.effects)

    def test_music_is_the_whole_soundtrack_when_nothing_is_narrated(self):
        music = FakeAudio(duration=60.0)

        with (
            patch.object(layers, "AudioFileClip", return_value=music),
            patch.object(layers, "CompositeAudioClip") as composite,
        ):
            mixed = handle_music(self.video, None, duration=25.0)

        composite.assert_not_called()
        self.assertIs(mixed, music)

    def test_turns_the_music_down_by_the_configured_amount(self):
        music = FakeAudio(duration=60.0)
        self.video.settings["music_volume"] = 0.5

        with (
            patch.object(layers, "AudioFileClip", return_value=music),
            patch.object(layers, "CompositeAudioClip"),
        ):
            handle_music(self.video, None, duration=25.0)

        self.assertIn("volumex", music.effects)
