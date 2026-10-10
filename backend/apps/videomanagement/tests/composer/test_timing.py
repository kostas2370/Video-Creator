import numpy as np
from django.test import SimpleTestCase
from moviepy.editor import AudioClip, VideoClip

from ...utils.composer.timing import align_audio, hold_scene


class SceneTimingTests(SimpleTestCase):
    def test_pause_holds_the_final_visual_and_then_adds_silence(self):
        visual = VideoClip(lambda t: np.full((8, 8, 3), int(t * 100), dtype=np.uint8), duration=2)
        audio = AudioClip(lambda t: np.ones((len(t), 2)) if isinstance(t, np.ndarray) else np.ones(2), duration=2, fps=44100)
        extended, resources = hold_scene(visual, 0.75)
        padded = align_audio(audio, extended.duration)
        try:
            self.assertEqual(extended.duration, 2.75)
            self.assertEqual(padded.duration, 2.75)
            np.testing.assert_array_equal(extended.get_frame(2.5), visual.get_frame(2 - 1 / 24))
            self.assertFalse(np.array_equal(extended.get_frame(2.5), visual.get_frame(0)))
            np.testing.assert_allclose(padded.get_frame(1), [1, 1])
            np.testing.assert_allclose(padded.get_frame(2.5), [0, 0])
        finally:
            for clip in [extended, padded, audio, *resources]:
                clip.close()

    def test_silent_scene_has_a_track_for_its_entire_timeline_slot(self):
        audio = align_audio(None, 5)
        try:
            self.assertEqual(audio.duration, 5)
            np.testing.assert_allclose(audio.get_frame(np.array([0, 4.9])), np.zeros((2, 2)))
        finally:
            audio.close()
