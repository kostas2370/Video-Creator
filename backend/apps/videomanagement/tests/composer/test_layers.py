from unittest.mock import patch

from django.test import SimpleTestCase

from ...baker_recipes import background, music, video
from ...utils.composer import layers
from ...utils.composer.layers import handle_background, handle_music
from ..doubles import FakeAudio, FakeClip


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


class HandleBackgroundTests(SimpleTestCase):
    def test_just_sizes_the_video_when_there_is_no_background(self):
        clip = FakeClip()

        self.assertIs(handle_background(10.0, None, clip), clip)
        self.assertEqual(clip.effects, ["resize"])

    def test_composites_the_video_over_a_still_background(self):
        behind = background.prepare()
        composited = FakeClip()

        with (
            patch.object(layers, "ImageClip", return_value=FakeClip()) as image,
            patch.object(layers, "VideoFileClip") as footage,
            patch.object(layers, "CompositeVideoClip", return_value=composited),
        ):
            handle_background(10.0, behind, FakeClip())

        image.assert_called_once()
        footage.assert_not_called()

    def test_composites_the_video_over_a_moving_background(self):
        behind = background.prepare(file="media/other/backgrounds/bg.mp4")

        with (
            patch.object(layers, "ImageClip") as image,
            patch.object(layers, "VideoFileClip", return_value=FakeClip()) as footage,
            patch.object(layers, "CompositeVideoClip", return_value=FakeClip()),
        ):
            handle_background(10.0, behind, FakeClip())

        footage.assert_called_once()
        image.assert_not_called()

    def test_keys_out_the_colour_the_background_names(self):
        behind = background.prepare(color="0,255,0", through=100)
        final = FakeClip()

        with (
            patch.object(layers, "ImageClip", return_value=FakeClip()),
            patch.object(layers, "CompositeVideoClip", return_value=FakeClip()),
        ):
            handle_background(10.0, behind, final)

        self.assertIn("fx", [e.split(":")[0] for e in final.effects])
