from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from model_bakery import baker

from ..utils.video_utils import clip_audio, handle_audio


def a_clip(audio=None):
    """A stand-in for a moviepy VideoFileClip carrying (or missing) an audio track."""
    clip = MagicMock()
    clip.audio = audio
    return clip


class ClipAudioTests(SimpleTestCase):
    """clip_audio: a scene visual's own soundtrack, when it is meant to be heard."""

    def test_returns_the_clips_audio_when_the_scene_is_flagged_with_audio(self):
        track = MagicMock()
        scene_image = baker.prepare_recipe(
            "videomanagement.video_scene_image_with_audio"
        )

        with patch(
            "apps.videomanagement.utils.video_utils.VideoFileClip",
            return_value=a_clip(track),
        ):
            self.assertIs(clip_audio(scene_image), track)

    def test_returns_none_for_a_silent_clip(self):
        scene_image = baker.prepare_recipe("videomanagement.video_scene_image")

        with patch(
            "apps.videomanagement.utils.video_utils.VideoFileClip"
        ) as video_file_clip:
            self.assertIsNone(clip_audio(scene_image))

        # Not flagged, so the file is never opened at all.
        video_file_clip.assert_not_called()

    def test_returns_none_without_a_scene_image(self):
        self.assertIsNone(clip_audio(None))

    def test_returns_none_when_the_scene_image_has_no_file(self):
        scene_image = baker.prepare_recipe(
            "videomanagement.video_scene_image_with_audio", file=None
        )

        self.assertIsNone(clip_audio(scene_image))

    def test_returns_none_when_the_file_carries_no_audio_track(self):
        scene_image = baker.prepare_recipe(
            "videomanagement.video_scene_image_with_audio"
        )

        with patch(
            "apps.videomanagement.utils.video_utils.VideoFileClip",
            return_value=a_clip(None),
        ):
            self.assertIsNone(clip_audio(scene_image))

    def test_returns_none_when_the_file_cannot_be_opened(self):
        scene_image = baker.prepare_recipe(
            "videomanagement.video_scene_image_with_audio"
        )

        with patch(
            "apps.videomanagement.utils.video_utils.VideoFileClip",
            side_effect=OSError("not a video"),
        ):
            # A broken clip loses its sound rather than failing the whole render.
            self.assertIsNone(clip_audio(scene_image))


class HandleAudioTests(SimpleTestCase):
    """handle_audio: what a narrated scene's soundtrack is built from."""

    def setUp(self):
        self.silence = MagicMock(name="silence")
        patcher = patch(
            "apps.videomanagement.utils.video_utils.AudioFileClip",
            return_value=self.silence,
        )
        self.audio_file_clip = patcher.start()
        self.addCleanup(patcher.stop)

    def test_falls_back_to_silence_when_the_scene_has_neither_narration_nor_a_clip(
        self,
    ):
        scene = baker.prepare_recipe("videomanagement.scene")
        scene_image = baker.prepare_recipe("videomanagement.scene_image")

        self.assertIs(handle_audio(scene, scene_image), self.silence)

    def test_pads_the_last_silent_scene_so_the_video_does_not_cut_off(self):
        scene = baker.prepare_recipe(
            "videomanagement.last_scene", file="media/speech/line.wav"
        )
        scene_image = baker.prepare_recipe("videomanagement.scene_image")
        padded = MagicMock(name="padded")

        with patch(
            "apps.videomanagement.utils.video_utils.concatenate_audioclips",
            return_value=padded,
        ) as concatenate:
            self.assertIs(handle_audio(scene, scene_image), padded)

        narration, *tail = concatenate.call_args.args[0]
        self.assertIs(narration, self.silence)  # the patched AudioFileClip
        self.assertEqual(tail, [self.silence, self.silence])

    def test_does_not_pad_a_last_scene_that_plays_its_own_audio(self):
        # The clip's own track already runs to the end of the picture, so the two
        # extra beats of silence would show up as a hang.
        scene = baker.prepare_recipe("videomanagement.last_scene")
        scene_image = baker.prepare_recipe(
            "videomanagement.video_scene_image_with_audio"
        )
        track = MagicMock(name="track")

        with (
            patch(
                "apps.videomanagement.utils.video_utils.VideoFileClip",
                return_value=a_clip(track),
            ),
            patch(
                "apps.videomanagement.utils.video_utils.concatenate_audioclips"
            ) as concatenate,
        ):
            self.assertIs(handle_audio(scene, scene_image), track)

        concatenate.assert_not_called()

    def test_mixes_the_clips_own_audio_over_the_narration(self):
        scene = baker.prepare_recipe(
            "videomanagement.scene", file="media/speech/line.wav"
        )
        scene_image = baker.prepare_recipe(
            "videomanagement.video_scene_image_with_audio"
        )
        track = MagicMock(name="track")
        mixed = MagicMock(name="mixed")

        with (
            patch(
                "apps.videomanagement.utils.video_utils.VideoFileClip",
                return_value=a_clip(track),
            ),
            patch(
                "apps.videomanagement.utils.video_utils.CompositeAudioClip",
                return_value=mixed,
            ) as composite,
        ):
            self.assertIs(handle_audio(scene, scene_image), mixed)

        self.assertEqual(composite.call_args.args[0][1], track)
