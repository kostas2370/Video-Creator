from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from ...baker_recipes import (
    background,
    last_scene,
    scene,
    scene_image,
    video_scene_image,
    video_scene_image_with_audio,
)
from ...utils.composer import clips
from ...utils.composer.clips import (
    clip_audio,
    handle_audio,
    handle_image,
    handle_video,
    process_scene,
)
from ..doubles import FakeAudio, FakeClip


def a_clip(audio=None):
    clip = MagicMock()
    clip.audio = audio
    return clip


class ClipAudioTests(SimpleTestCase):
    def test_returns_the_clips_audio_when_the_scene_is_flagged_with_audio(self):
        track = MagicMock()
        scene_image = video_scene_image_with_audio.prepare()

        with patch(
            "apps.videomanagement.utils.composer.clips.VideoFileClip",
            return_value=a_clip(track),
        ):
            self.assertIs(clip_audio(scene_image), track)

    def test_returns_none_for_a_silent_clip(self):
        scene_image = video_scene_image.prepare()

        with patch(
            "apps.videomanagement.utils.composer.clips.VideoFileClip"
        ) as video_file_clip:
            self.assertIsNone(clip_audio(scene_image))

        video_file_clip.assert_not_called()

    def test_returns_none_without_a_scene_image(self):
        self.assertIsNone(clip_audio(None))

    def test_returns_none_when_the_scene_image_has_no_file(self):
        scene_image = video_scene_image_with_audio.prepare(file=None)

        self.assertIsNone(clip_audio(scene_image))

    def test_returns_none_when_the_file_carries_no_audio_track(self):
        scene_image = video_scene_image_with_audio.prepare()

        with patch(
            "apps.videomanagement.utils.composer.clips.VideoFileClip",
            return_value=a_clip(None),
        ):
            self.assertIsNone(clip_audio(scene_image))

    def test_returns_none_when_the_file_cannot_be_opened(self):
        scene_image = video_scene_image_with_audio.prepare()

        with patch(
            "apps.videomanagement.utils.composer.clips.VideoFileClip",
            side_effect=OSError("not a video"),
        ):
            # A broken clip loses its sound rather than failing the whole render.
            self.assertIsNone(clip_audio(scene_image))


class HandleAudioTests(SimpleTestCase):
    def setUp(self):
        self.silence = MagicMock(name="silence")
        patcher = patch(
            "apps.videomanagement.utils.composer.clips.AudioFileClip",
            return_value=self.silence,
        )
        self.audio_file_clip = patcher.start()
        self.addCleanup(patcher.stop)

    def test_falls_back_to_silence_when_the_scene_has_neither_narration_nor_a_clip(
        self,
    ):
        line = scene.prepare()
        image = scene_image.prepare()

        self.assertIs(handle_audio(line, image), self.silence)

    def test_pads_the_last_silent_scene_so_the_video_does_not_cut_off(self):
        line = last_scene.prepare(file="media/speech/line.wav")
        image = scene_image.prepare()
        padded = MagicMock(name="padded")

        with patch(
            "apps.videomanagement.utils.composer.clips.concatenate_audioclips",
            return_value=padded,
        ) as concatenate:
            self.assertIs(handle_audio(line, image), padded)

        narration, *tail = concatenate.call_args.args[0]
        self.assertIs(narration, self.silence)  # the patched AudioFileClip
        self.assertEqual(tail, [self.silence, self.silence])

    def test_does_not_pad_a_last_scene_that_plays_its_own_audio(self):
        scene = last_scene.prepare()
        scene_image = video_scene_image_with_audio.prepare()
        track = MagicMock(name="track")

        with (
            patch(
                "apps.videomanagement.utils.composer.clips.VideoFileClip",
                return_value=a_clip(track),
            ),
            patch(
                "apps.videomanagement.utils.composer.clips.concatenate_audioclips"
            ) as concatenate,
        ):
            self.assertIs(handle_audio(scene, scene_image), track)

        concatenate.assert_not_called()

    def test_mixes_the_clips_own_audio_over_the_narration(self):
        line = scene.prepare(file="media/speech/line.wav")
        image = video_scene_image_with_audio.prepare()
        track = MagicMock(name="track")
        mixed = MagicMock(name="mixed")

        with (
            patch(
                "apps.videomanagement.utils.composer.clips.VideoFileClip",
                return_value=a_clip(track),
            ),
            patch(
                "apps.videomanagement.utils.composer.clips.CompositeAudioClip",
                return_value=mixed,
            ) as composite,
        ):
            self.assertIs(handle_audio(line, image), mixed)

        self.assertEqual(composite.call_args.args[0][1], track)


class HandleImageTests(SimpleTestCase):
    def setUp(self):
        self.scene_image = scene_image.prepare()

    def test_holds_the_still_for_as_long_as_the_narration_runs(self):
        clip = FakeClip()
        with patch.object(clips, "ImageClip", return_value=clip):
            image = handle_image(FakeAudio(duration=6.0), self.scene_image, None)

        self.assertEqual(image.duration, 6.0)
        self.assertIn("fadein", image.effects)
        self.assertIn("fadeout", image.effects)

    @override_settings(SILENT_SCENE_SECONDS=7)
    def test_falls_back_to_the_configured_length_when_nothing_is_spoken(self):
        clip = FakeClip()
        with patch.object(clips, "ImageClip", return_value=clip):
            image = handle_image(None, self.scene_image, None)

        self.assertEqual(image.duration, 7)

    def test_shrinks_the_still_to_sit_inside_a_background(self):
        still = MagicMock()
        behind = background.prepare()

        with patch.object(
            clips, "ImageClip", side_effect=[still, FakeClip(size=(1000, 500))]
        ):
            handle_image(FakeAudio(), self.scene_image, behind)

        still.resize.assert_called_once_with((650, 325))

    def test_leaves_the_source_still_on_disk_untouched(self):
        behind = background.prepare()

        with (
            patch.object(
                clips,
                "ImageClip",
                side_effect=[MagicMock(), FakeClip(size=(1000, 500))],
            ),
            patch("PIL.Image.open") as opened,
        ):
            handle_image(FakeAudio(), self.scene_image, behind)

        opened.assert_not_called()

    def test_raises_when_the_still_cannot_be_opened(self):
        with patch.object(clips, "ImageClip", side_effect=OSError("corrupt")):
            with self.assertRaises(Exception):
                handle_image(FakeAudio(), self.scene_image, None)


class HandleVideoTests(SimpleTestCase):
    def setUp(self):
        self.scene_image = video_scene_image.prepare()

    def fit(self, clip_duration, audio):
        clip = FakeClip(duration=clip_duration)
        with patch.object(clips, "VideoFileClip", return_value=clip):
            return handle_video(audio, self.scene_image)

    def test_trims_a_clip_that_outruns_the_narration(self):
        fitted = self.fit(10.0, FakeAudio(duration=6.0))

        self.assertEqual(fitted.duration, 6.0)
        self.assertIn("subclip", fitted.effects)

    def test_freezes_the_last_frame_when_the_narration_outruns_the_clip(self):
        fitted = self.fit(12.0, FakeAudio(duration=20.0))

        self.assertEqual(fitted.duration, 20.0)
        self.assertIn("fx:freeze", fitted.effects)

    def test_leaves_a_clip_that_already_matches_alone(self):
        fitted = self.fit(6.0, FakeAudio(duration=6.0))

        self.assertNotIn("subclip", fitted.effects)

    def test_lets_the_clip_run_at_its_own_length_when_nothing_is_spoken(self):
        fitted = self.fit(9.0, None)

        self.assertEqual(fitted.duration, 9.0)
        self.assertNotIn("subclip", fitted.effects)

    def test_always_strips_the_clips_own_audio(self):
        self.assertIn("without_audio", self.fit(6.0, FakeAudio(6.0)).effects)

    def test_raises_a_useful_error_when_the_file_will_not_open(self):
        with patch.object(clips, "VideoFileClip", side_effect=OSError("bad")):
            with self.assertRaises(ValueError):
                handle_video(FakeAudio(), self.scene_image)


class ProcessSceneTests(SimpleTestCase):
    def setUp(self):
        patcher = patch.object(clips, "ImageClip", return_value=FakeClip())
        self.image_clip = patcher.start()
        self.addCleanup(patcher.stop)

    def test_sends_a_still_to_handle_image(self):
        image = scene_image.prepare()

        with patch.object(clips, "handle_image") as handle:
            process_scene(image, FakeAudio(), None)

        handle.assert_called_once()

    def test_sends_footage_to_handle_video(self):
        scene_image = video_scene_image.prepare()

        with patch.object(clips, "handle_video") as handle:
            process_scene(scene_image, FakeAudio(), None)

        handle.assert_called_once()

    def test_falls_back_to_black_for_an_unsupported_file_type(self):
        image = scene_image.prepare(file="media/images/notes.txt")
        black = FakeClip()

        with patch.object(clips, "ImageClip", return_value=black):
            self.assertIs(process_scene(image, FakeAudio(3.0), None), black)

        self.assertEqual(black.duration, 3.0)

    def test_falls_back_to_black_when_the_visual_fails_to_load(self):
        scene_image = video_scene_image.prepare()
        black = FakeClip()

        with (
            patch.object(clips, "ImageClip", return_value=black),
            patch.object(clips, "handle_video", side_effect=ValueError("bad")),
        ):
            self.assertIs(process_scene(scene_image, FakeAudio(3.0), None), black)

    def test_falls_back_to_black_without_a_scene_image(self):
        black = FakeClip()

        with patch.object(clips, "ImageClip", return_value=black):
            self.assertIs(process_scene(None, FakeAudio(3.0), None), black)

    def test_falls_back_to_black_when_the_provider_left_no_file(self):
        image = scene_image.prepare(file=None)
        black = FakeClip()

        with patch.object(clips, "ImageClip", return_value=black):
            self.assertIs(process_scene(image, FakeAudio(3.0), None), black)
