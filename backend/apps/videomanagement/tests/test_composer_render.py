from unittest.mock import patch

from django.test import TestCase

from ..baker_recipes import (
    narrated_scene,
    scene,
    scene_image,
    video,
    video_scene_image_with_audio,
)
from ..utils.composer import render
from ..utils.composer.render import make_video
from ..utils.exceptions import RenderFailedException
from .doubles import FakeAudio, FakeClip


class MakeVideoTests(TestCase):
    def setUp(self):
        self.video = video.make(status="READY")
        self.scenes = narrated_scene.make(prompt=self.video.prompt, _quantity=2)
        for line in self.scenes:
            scene_image.make(scene=line)

        self.final = FakeClip()
        patches = {
            "concatenate_videoclips": self.final,
            "handle_final_video": self.final,
            "process_scene": FakeClip(),
            "concatenate_audioclips": FakeAudio(),
        }
        for name, value in patches.items():
            patcher = patch.object(render, name, return_value=value)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_renders_every_scene_and_marks_the_video_completed(self):
        with patch.object(render, "handle_audio", return_value=FakeAudio()):
            rendered = make_video(self.video)

        self.assertEqual(self.process_scene.call_count, 2)
        self.assertEqual(rendered.status, "COMPLETED")
        self.assertEqual(rendered.output, f"{self.video.dir_name}/output_video.mp4")

    def test_writes_an_mp4_rather_than_only_marking_the_row_completed(self):
        with patch.object(render, "handle_audio", return_value=FakeAudio()):
            make_video(self.video)

        self.assertIn("write_videofile", self.final.effects)

    def test_renders_a_video_the_view_has_already_marked_rendering(self):
        # render_video marks the row before queueing, so the worker always finds it
        # in RENDERING rather than in the state the client asked from.
        self.video.status = "RENDERING"
        self.video.save()

        with patch.object(render, "handle_audio", return_value=FakeAudio()):
            rendered = make_video(self.video)

        self.assertEqual(rendered.status, "COMPLETED")

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

        with patch.object(render, "handle_audio") as handle_audio_call:
            make_video(self.video)

        handle_audio_call.assert_not_called()
        self.concatenate_audioclips.assert_not_called()

    def test_keeps_the_clips_own_sound_when_the_video_has_no_narration(self):
        self.video.settings = dict(subtitles=False, narration=False)
        self.video.save()
        self.video.prompt.scenes.all().delete()
        line = scene.make(prompt=self.video.prompt)
        video_scene_image_with_audio.make(scene=line)

        with patch.object(render, "clip_audio", return_value=FakeAudio()) as clip:
            make_video(self.video)

        clip.assert_called_once()
        self.concatenate_audioclips.assert_called_once()

    def test_times_subtitles_against_the_narration(self):
        self.video.settings = dict(subtitles=True, narration=True)
        self.video.save()

        with (
            patch.object(render, "handle_audio", return_value=FakeAudio(duration=4.0)),
            patch.object(
                render, "create_subtitle_clip", return_value=FakeClip()
            ) as subtitle,
        ):
            make_video(self.video)

        self.assertEqual(subtitle.call_count, 2)
        self.assertEqual(subtitle.call_args.args[1], 4.0)

    def test_skips_a_subtitle_that_could_not_be_drawn(self):
        self.video.settings = dict(subtitles=True, narration=True)
        self.video.save()

        with (
            patch.object(render, "handle_audio", return_value=FakeAudio()),
            patch.object(render, "create_subtitle_clip", return_value=None),
        ):
            make_video(self.video)

        self.assertEqual(self.handle_final_video.call_args.args[4], [])

    def test_writes_no_subtitles_when_there_is_no_narration_to_time_them_against(self):
        self.video.settings = dict(subtitles=True, narration=False)
        self.video.save()

        with patch.object(render, "create_subtitle_clip") as subtitle:
            make_video(self.video)

        subtitle.assert_not_called()

    def test_marks_the_video_rendering_while_the_work_is_in_flight(self):
        seen = []

        def record(*args, **kwargs):
            seen.append(type(self.video).objects.get(pk=self.video.pk).status)
            return FakeClip()

        self.process_scene.side_effect = record
        with patch.object(render, "handle_audio", return_value=FakeAudio()):
            make_video(self.video)

        self.assertEqual(set(seen), {"RENDERING"})

    def test_closes_every_clip_even_when_the_render_fails(self):
        audio, clip = FakeAudio(), FakeClip()
        self.process_scene.return_value = clip
        self.handle_final_video.side_effect = RuntimeError("encoder died")

        with patch.object(render, "handle_audio", return_value=audio):
            with self.assertRaises(RuntimeError):
                make_video(self.video)

        self.assertTrue(clip.closed)
        self.assertTrue(audio.closed)
