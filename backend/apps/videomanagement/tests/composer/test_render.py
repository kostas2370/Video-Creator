from unittest.mock import patch

from django.test import TestCase

from ...baker_recipes import (
    narrated_scene,
    scene,
    scene_image,
    video,
    video_scene_image_with_audio,
)
from ...utils.composer import render
from ...utils.composer.render import make_video
from ...utils.exceptions import RenderFailedException
from ..doubles import FakeAudio, FakeClip


class MakeVideoTests(TestCase):
    def setUp(self):
        self.video = video.make(status="READY")
        self.scenes = narrated_scene.make(video=self.video, _quantity=2)
        for line in self.scenes:
            scene_image.make(scene=line)

        self.final = FakeClip()
        patches = {
            "compose_transitions": (self.final, []),
            "handle_final_video": self.final,
            "process_scene": FakeClip(),
            "concatenate_audioclips": FakeAudio(),
        }
        for name, value in patches.items():
            patcher = patch.object(render, name, return_value=value)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

        patcher = patch("apps.videomanagement.services.subtitles.narration_duration", return_value=4)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_pause_shifts_next_subtitle_and_pads_audio_to_scene_duration(self):
        from moviepy.editor import ColorClip
        self.video.settings = {"subtitles": True}
        self.video.save()
        self.scenes[0].pause_after = 0.75
        self.scenes[0].save()
        with (
            patch.object(render, "handle_audio", return_value=FakeAudio(duration=4)),
            patch.object(render, "process_scene", side_effect=lambda *args: ColorClip((8, 8), color=(255, 0, 0)).set_duration(4)),
            patch.object(render, "create_subtitle_clip", side_effect=lambda *args, **kwargs: ColorClip((8, 8), color=(0, 0, 0)).set_duration(args[1])) as subtitle,
            patch.object(render, "align_audio", side_effect=lambda audio, duration: FakeAudio(duration=duration)) as align,
        ):
            make_video(self.video)
        self.assertEqual([call.args[1] for call in align.call_args_list], [4.75, 4])
        self.assertEqual([clip.duration for clip in self.compose_transitions.call_args.args[0]], [4.75, 4])
        self.assertEqual(subtitle.call_args.args[1], 4)
        self.assertEqual([clip.start for clip in self.handle_final_video.call_args.args[4]], [0, 4.75])

    def test_render_uses_the_shared_phrase_cues_and_keeps_caption_gaps(self):
        from moviepy.editor import ColorClip
        from ...services.subtitles import scene_cues
        self.video.settings = {"subtitles": True}
        self.video.save()
        for line in self.scenes:
            line.text = "Hello there. A longer sentence for our viewers."
            line.save()
        self.scenes[0].pause_after = 0.75
        self.scenes[0].save()
        expected = scene_cues(self.scenes[0], duration=4) + scene_cues(self.scenes[1], duration=4, offset=4.75)
        with (
            patch.object(render, "handle_audio", return_value=FakeAudio(duration=4)),
            patch.object(render, "process_scene", side_effect=lambda *args: ColorClip((8, 8), color=(20, 30, 40)).set_duration(4)),
            patch.object(render, "create_subtitle_clip", side_effect=lambda *args, **kwargs: ColorClip((8, 8), color=(0, 0, 0)).set_duration(args[1])) as caption,
            patch.object(render, "align_audio", side_effect=lambda audio, duration: FakeAudio(duration=duration)),
        ):
            make_video(self.video)
        self.assertEqual([call.args[0] for call in caption.call_args_list], [cue.text for cue in expected])
        self.assertEqual([(clip.start, clip.end) for clip in self.handle_final_video.call_args.args[4]], [(cue.start, cue.end) for cue in expected])
        self.assertEqual(expected[1].end, 4)
        self.assertEqual(expected[2].start, 4.75)

    def test_cut_removes_both_fades_at_only_the_selected_join(self):
        first, second = self.scenes
        first.transition_after = "CUT"
        first.save()
        third = narrated_scene.make(video=self.video)
        scene_image.make(scene=third)
        with patch.object(render, "handle_audio", return_value=FakeAudio()):
            make_video(self.video)
        self.assertEqual(self.compose_transitions.call_args.args[1], [("CUT", None), ("FADE", None), ("FADE", None)])
        self.assertTrue(all(not call.kwargs for call in self.process_scene.call_args_list))

    def test_video_default_is_used_and_scene_override_wins(self):
        self.video.settings = {"transition_default": "DISSOLVE", "transition_duration": 0.75}
        self.video.save()
        self.scenes[1].transition_after = "CUT"
        self.scenes[1].save()
        with patch.object(render, "handle_audio", return_value=FakeAudio()):
            make_video(self.video)
        self.assertEqual(self.compose_transitions.call_args.args[1], [("DISSOLVE", 0.75), ("CUT", 0.75)])
        self.assertEqual(self.compose_transitions.call_args.kwargs["opening_duration"], 0.75)

    def test_existing_scenes_keep_their_fades_by_default(self):
        with patch.object(render, "handle_audio", return_value=FakeAudio()):
            make_video(self.video)
        self.assertEqual(self.compose_transitions.call_args.args[1], [("FADE", None), ("FADE", None)])

    def test_renders_in_position_order_after_reordering_scenes(self):
        first, second = self.scenes
        type(first).objects.filter(pk=first.pk).update(position=3)
        type(second).objects.filter(pk=second.pk).update(position=1)
        type(first).objects.filter(pk=first.pk).update(position=2)
        with patch.object(render, "handle_audio", return_value=FakeAudio()) as audio:
            make_video(self.video)
        self.assertEqual([call.args[0].pk for call in audio.call_args_list], [second.pk, first.pk])

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
        self.video.scenes.all().delete()

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
        self.video.scenes.all().delete()
        line = scene.make(video=self.video)
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
