from types import SimpleNamespace

from django.test import SimpleTestCase
from moviepy.editor import ColorClip

from ...utils.composer.transitions import apply_fades, compose_transitions, scene_transition


class TransitionTests(SimpleTestCase):
    def compose(self, style, duration, lengths=(2, 2)):
        clips = [ColorClip((16, 16), color=color, duration=length)
                 for color, length in zip([(255, 0, 0), (0, 0, 255)], lengths)]
        video, resources = compose_transitions(clips, [(style, duration), ("CUT", None)])
        for clip in [*clips, *resources, video]:
            self.addCleanup(clip.close)
        return video

    def test_fades_use_the_requested_duration_and_keep_clip_length(self):
        source = ColorClip((16, 16), color=(255, 0, 0), duration=1)
        faded = apply_fades(source, fade_in_duration=3, fade_out_duration=3)
        self.addCleanup(source.close)
        self.addCleanup(faded.close)
        self.assertEqual(faded.duration, 1)
        self.assertAlmostEqual(faded.get_frame(0.25)[0, 0, 0], 127, delta=2)
        self.assertAlmostEqual(faded.get_frame(0.75)[0, 0, 0], 127, delta=2)

    def test_dissolve_blends_pixels_without_shortening_the_video(self):
        video = self.compose("DISSOLVE", 0.5)
        self.assertEqual(video.duration, 4)
        self.assertEqual(tuple(video.get_frame(1.9)[0, 0]), (255, 0, 0))
        red, green, blue = video.get_frame(2.25)[0, 0]
        self.assertAlmostEqual(red, 127, delta=2)
        self.assertEqual(green, 0)
        self.assertAlmostEqual(blue, 127, delta=2)
        self.assertEqual(tuple(video.get_frame(2.6)[0, 0]), (0, 0, 255))

    def test_long_dissolve_is_clamped_for_a_short_scene(self):
        video = self.compose("DISSOLVE", 3, lengths=(0.2, 0.3))
        self.assertAlmostEqual(video.duration, 0.5)
        self.assertEqual(tuple(video.get_frame(0.31)[0, 0]), (0, 0, 255))

    def test_cut_has_no_blending(self):
        video = self.compose("CUT", 1)
        self.assertEqual(tuple(video.get_frame(2)[0, 0]), (0, 0, 255))

    def test_opening_fades_only_when_the_video_default_is_fade(self):
        for style in ("CUT", "DISSOLVE", "FADE"):
            with self.subTest(style=style):
                source = ColorClip((16, 16), color=(255, 0, 0), duration=2)
                video, resources = compose_transitions(
                    [source], [("CUT", None)], opening_style=style, opening_duration=0.5,
                )
                for clip in [source, *resources, video]:
                    self.addCleanup(clip.close)
                expected = 127 if style == "FADE" else 255
                self.assertAlmostEqual(video.get_frame(0.25)[0, 0, 0], expected, delta=2)
                self.assertEqual(video.duration, 2)

    def test_style_and_duration_inherit_independently(self):
        settings = {"transition_default": "DISSOLVE", "transition_duration": 0.75}
        scene = SimpleNamespace(transition_after="DEFAULT", transition_duration=None)
        self.assertEqual(scene_transition(scene, settings), ("DISSOLVE", 0.75))
        scene.transition_after = "FADE"
        self.assertEqual(scene_transition(scene, settings), ("FADE", 0.75))
        scene.transition_duration = 0.25
        self.assertEqual(scene_transition(scene, settings), ("FADE", 0.25))
