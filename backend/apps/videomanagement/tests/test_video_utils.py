from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings
from model_bakery import baker

from ..utils import video_utils
from ..utils.exceptions import RenderFailedException
from ..utils.video_utils import (
    check_if_image,
    check_if_video,
    clip_audio,
    create_subtitle_clip,
    handle_audio,
    handle_background,
    handle_image,
    handle_music,
    handle_video,
    make_video,
    process_scene,
)
from .doubles import FakeAudio, FakeClip


def a_clip(audio=None):
    clip = MagicMock()
    clip.audio = audio
    return clip


class ClipAudioTests(SimpleTestCase):
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


class FileTypeTests(SimpleTestCase):
    def test_recognises_stills_by_extension_whatever_the_case(self):
        for path in ("a.jpg", "a.JPEG", "a/b.PNG"):
            with self.subTest(path=path):
                self.assertTrue(check_if_image(path))
                self.assertFalse(check_if_video(path))

    def test_recognises_footage_by_extension(self):
        for path in ("a.mp4", "a/b.AVI"):
            with self.subTest(path=path):
                self.assertTrue(check_if_video(path))
                self.assertFalse(check_if_image(path))

    def test_recognises_neither_for_anything_else(self):
        self.assertFalse(check_if_image("a.wav"))
        self.assertFalse(check_if_video("a.wav"))


class HandleImageTests(SimpleTestCase):
    def setUp(self):
        self.scene_image = baker.prepare_recipe("videomanagement.scene_image")

    def test_holds_the_still_for_as_long_as_the_narration_runs(self):
        clip = FakeClip()
        with patch.object(video_utils, "ImageClip", return_value=clip):
            image = handle_image(FakeAudio(duration=6.0), self.scene_image, None)

        self.assertEqual(image.duration, 6.0)
        self.assertIn("fadein", image.effects)
        self.assertIn("fadeout", image.effects)

    @override_settings(SILENT_SCENE_SECONDS=7)
    def test_falls_back_to_the_configured_length_when_nothing_is_spoken(self):
        clip = FakeClip()
        with patch.object(video_utils, "ImageClip", return_value=clip):
            image = handle_image(None, self.scene_image, None)

        self.assertEqual(image.duration, 7)

    def test_shrinks_the_still_to_sit_inside_a_background(self):
        clip = FakeClip(size=(1000, 500))
        opened = MagicMock()
        opened.convert.return_value.resize.return_value = opened

        background = baker.prepare_recipe("videomanagement.background")
        with (
            patch.object(video_utils, "ImageClip", return_value=clip),
            patch.object(video_utils.Image, "open", return_value=opened),
        ):
            handle_image(FakeAudio(), self.scene_image, background)

        opened.convert.return_value.resize.assert_called_once_with((650, 325))

    def test_raises_when_the_still_cannot_be_opened(self):
        with patch.object(video_utils, "ImageClip", side_effect=OSError("corrupt")):
            with self.assertRaises(Exception):
                handle_image(FakeAudio(), self.scene_image, None)


class HandleVideoTests(SimpleTestCase):
    def setUp(self):
        self.scene_image = baker.prepare_recipe("videomanagement.video_scene_image")

    def fit(self, clip_duration, audio):
        clip = FakeClip(duration=clip_duration)
        with patch.object(video_utils, "VideoFileClip", return_value=clip):
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
        with patch.object(video_utils, "VideoFileClip", side_effect=OSError("bad")):
            with self.assertRaises(ValueError):
                handle_video(FakeAudio(), self.scene_image)


class ProcessSceneTests(SimpleTestCase):
    def setUp(self):
        patcher = patch.object(video_utils, "ImageClip", return_value=FakeClip())
        self.image_clip = patcher.start()
        self.addCleanup(patcher.stop)

    def test_sends_a_still_to_handle_image(self):
        scene_image = baker.prepare_recipe("videomanagement.scene_image")

        with patch.object(video_utils, "handle_image") as handle:
            process_scene(scene_image, FakeAudio(), None)

        handle.assert_called_once()

    def test_sends_footage_to_handle_video(self):
        scene_image = baker.prepare_recipe("videomanagement.video_scene_image")

        with patch.object(video_utils, "handle_video") as handle:
            process_scene(scene_image, FakeAudio(), None)

        handle.assert_called_once()

    def test_falls_back_to_black_for_an_unsupported_file_type(self):
        scene_image = baker.prepare_recipe(
            "videomanagement.scene_image", file="media/images/notes.txt"
        )
        black = FakeClip()

        with patch.object(video_utils, "ImageClip", return_value=black):
            self.assertIs(process_scene(scene_image, FakeAudio(3.0), None), black)

        self.assertEqual(black.duration, 3.0)

    def test_falls_back_to_black_when_the_visual_fails_to_load(self):
        scene_image = baker.prepare_recipe("videomanagement.video_scene_image")
        black = FakeClip()

        with (
            patch.object(video_utils, "ImageClip", return_value=black),
            patch.object(video_utils, "handle_video", side_effect=ValueError("bad")),
        ):
            self.assertIs(process_scene(scene_image, FakeAudio(3.0), None), black)


class HandleMusicTests(SimpleTestCase):
    def setUp(self):
        self.video = baker.prepare_recipe("videomanagement.video")
        self.video.music = baker.prepare_recipe("videomanagement.music")

    def test_loops_music_that_is_shorter_than_the_video(self):
        music = FakeAudio(duration=10.0)

        with (
            patch.object(video_utils, "AudioFileClip", return_value=music),
            patch.object(
                video_utils, "concatenate_audioclips", return_value=music
            ) as concatenate,
            patch.object(video_utils, "CompositeAudioClip") as composite,
        ):
            handle_music(self.video, FakeAudio(25.0), duration=25.0)

        # 25s of video over a 10s track: three copies, then trimmed back to 25s.
        self.assertEqual(len(concatenate.call_args.args[0]), 3)
        composite.assert_called_once()

    def test_trims_music_that_is_longer_than_the_video(self):
        music = FakeAudio(duration=60.0)

        with (
            patch.object(video_utils, "AudioFileClip", return_value=music),
            patch.object(video_utils, "concatenate_audioclips") as concatenate,
            patch.object(video_utils, "CompositeAudioClip"),
        ):
            handle_music(self.video, FakeAudio(25.0), duration=25.0)

        concatenate.assert_not_called()
        self.assertIn("subclip", music.effects)

    def test_music_is_the_whole_soundtrack_when_nothing_is_narrated(self):
        music = FakeAudio(duration=60.0)

        with (
            patch.object(video_utils, "AudioFileClip", return_value=music),
            patch.object(video_utils, "CompositeAudioClip") as composite,
        ):
            mixed = handle_music(self.video, None, duration=25.0)

        composite.assert_not_called()
        self.assertIs(mixed, music)

    def test_turns_the_music_down_by_the_configured_amount(self):
        music = FakeAudio(duration=60.0)
        self.video.settings["music_volume"] = 0.5

        with (
            patch.object(video_utils, "AudioFileClip", return_value=music),
            patch.object(video_utils, "CompositeAudioClip"),
        ):
            handle_music(self.video, None, duration=25.0)

        self.assertIn("volumex", music.effects)


class HandleBackgroundTests(SimpleTestCase):
    def test_just_sizes_the_video_when_there_is_no_background(self):
        clip = FakeClip()

        self.assertIs(handle_background(10.0, None, clip), clip)
        self.assertEqual(clip.effects, ["resize"])

    def test_composites_the_video_over_a_still_background(self):
        background = baker.prepare_recipe("videomanagement.background")
        composited = FakeClip()

        with (
            patch.object(video_utils, "ImageClip", return_value=FakeClip()) as image,
            patch.object(video_utils, "VideoFileClip") as video,
            patch.object(video_utils, "CompositeVideoClip", return_value=composited),
        ):
            handle_background(10.0, background, FakeClip())

        image.assert_called_once()
        video.assert_not_called()

    def test_composites_the_video_over_a_moving_background(self):
        background = baker.prepare_recipe(
            "videomanagement.background", file="media/other/backgrounds/bg.mp4"
        )

        with (
            patch.object(video_utils, "ImageClip") as image,
            patch.object(
                video_utils, "VideoFileClip", return_value=FakeClip()
            ) as video,
            patch.object(video_utils, "CompositeVideoClip", return_value=FakeClip()),
        ):
            handle_background(10.0, background, FakeClip())

        video.assert_called_once()
        image.assert_not_called()

    def test_keys_out_the_colour_the_background_names(self):
        background = baker.prepare_recipe(
            "videomanagement.background", color="0,255,0", through=100
        )
        final = FakeClip()

        with (
            patch.object(video_utils, "ImageClip", return_value=FakeClip()),
            patch.object(video_utils, "CompositeVideoClip", return_value=FakeClip()),
        ):
            handle_background(10.0, background, final)

        self.assertIn("fx", [e.split(":")[0] for e in final.effects])


class CreateSubtitleClipTests(SimpleTestCase):
    @override_settings(SUBTITLE_FONT="DejaVu-Sans")
    def test_builds_a_caption_that_lasts_as_long_as_the_line(self):
        clip = FakeClip()

        with patch.object(video_utils, "TextClip", return_value=clip) as text:
            subtitle = create_subtitle_clip("hello", duration=4.0)

        self.assertEqual(subtitle.duration, 4.0)
        self.assertEqual(text.call_args.kwargs["method"], "caption")
        self.assertEqual(text.call_args.kwargs["font"], "DejaVu-Sans")

    def test_returns_none_rather_than_failing_the_render_when_text_cannot_be_drawn(
        self,
    ):
        # ImageMagick is a separate binary and is not always configured.
        with patch.object(video_utils, "TextClip", side_effect=OSError("no convert")):
            self.assertIsNone(create_subtitle_clip("hello", 4.0))


class MakeVideoTests(TestCase):
    def setUp(self):
        self.video = baker.make_recipe("videomanagement.video", status="READY")
        self.scenes = baker.make_recipe(
            "videomanagement.narrated_scene", prompt=self.video.prompt, _quantity=2
        )
        for scene in self.scenes:
            baker.make_recipe("videomanagement.scene_image", scene=scene)

        self.final = FakeClip()
        patches = {
            "concatenate_videoclips": self.final,
            "handle_final_video": self.final,
            "process_scene": FakeClip(),
            "concatenate_audioclips": FakeAudio(),
        }
        for name, value in patches.items():
            patcher = patch.object(video_utils, name, return_value=value)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_renders_every_scene_and_marks_the_video_completed(self):
        with patch.object(video_utils, "handle_audio", return_value=FakeAudio()):
            rendered = make_video(self.video)

        self.assertEqual(self.process_scene.call_count, 2)
        self.assertEqual(rendered.status, "COMPLETED")
        self.assertEqual(rendered.output, f"{self.video.dir_name}/output_video.mp4")

    def test_writes_an_mp4_rather_than_only_marking_the_row_completed(self):
        with patch.object(video_utils, "handle_audio", return_value=FakeAudio()):
            make_video(self.video)

        self.assertIn("write_videofile", self.final.effects)

    def test_refuses_to_render_a_video_that_is_not_ready(self):
        self.video.status = "GENERATION"
        self.video.save()

        with self.assertRaises(RenderFailedException):
            make_video(self.video)

    def test_refuses_to_render_when_no_scene_produced_a_clip(self):
        self.video.prompt.scenes.all().delete()

        with self.assertRaises(RenderFailedException):
            make_video(self.video)

    def test_builds_no_voice_track_when_the_video_has_no_narration(self):
        self.video.settings = dict(subtitles=False, narration=False)
        self.video.save()

        with patch.object(video_utils, "handle_audio") as handle_audio_call:
            make_video(self.video)

        handle_audio_call.assert_not_called()
        self.concatenate_audioclips.assert_not_called()

    def test_keeps_the_clips_own_sound_when_the_video_has_no_narration(self):
        self.video.settings = dict(subtitles=False, narration=False)
        self.video.save()
        self.video.prompt.scenes.all().delete()
        scene = baker.make_recipe("videomanagement.scene", prompt=self.video.prompt)
        baker.make_recipe("videomanagement.video_scene_image_with_audio", scene=scene)

        with patch.object(video_utils, "clip_audio", return_value=FakeAudio()) as clip:
            make_video(self.video)

        clip.assert_called_once()
        self.concatenate_audioclips.assert_called_once()

    def test_times_subtitles_against_the_narration(self):
        self.video.settings = dict(subtitles=True, narration=True)
        self.video.save()

        with (
            patch.object(
                video_utils, "handle_audio", return_value=FakeAudio(duration=4.0)
            ),
            patch.object(
                video_utils, "create_subtitle_clip", return_value=FakeClip()
            ) as subtitle,
        ):
            make_video(self.video)

        self.assertEqual(subtitle.call_count, 2)
        self.assertEqual(subtitle.call_args.args[1], 4.0)

    def test_skips_a_subtitle_that_could_not_be_drawn(self):
        self.video.settings = dict(subtitles=True, narration=True)
        self.video.save()

        with (
            patch.object(video_utils, "handle_audio", return_value=FakeAudio()),
            patch.object(video_utils, "create_subtitle_clip", return_value=None),
        ):
            make_video(self.video)

        self.assertEqual(self.handle_final_video.call_args.args[4], [])

    def test_writes_no_subtitles_when_there_is_no_narration_to_time_them_against(self):
        self.video.settings = dict(subtitles=True, narration=False)
        self.video.save()

        with patch.object(video_utils, "create_subtitle_clip") as subtitle:
            make_video(self.video)

        subtitle.assert_not_called()

    def test_marks_the_video_rendering_while_the_work_is_in_flight(self):
        seen = []

        def record(*args, **kwargs):
            seen.append(type(self.video).objects.get(pk=self.video.pk).status)
            return FakeClip()

        self.process_scene.side_effect = record
        with patch.object(video_utils, "handle_audio", return_value=FakeAudio()):
            make_video(self.video)

        self.assertEqual(set(seen), {"RENDERING"})

    def test_closes_every_clip_even_when_the_render_fails(self):
        audio, clip = FakeAudio(), FakeClip()
        self.process_scene.return_value = clip
        self.handle_final_video.side_effect = RuntimeError("encoder died")

        with patch.object(video_utils, "handle_audio", return_value=audio):
            with self.assertRaises(RuntimeError):
                make_video(self.video)

        self.assertTrue(clip.closed)
        self.assertTrue(audio.closed)
