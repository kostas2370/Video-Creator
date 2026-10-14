import numpy as np
from django.test import SimpleTestCase
from moviepy.editor import AudioClip

from ...utils.composer.effects import apply_audio_fades


class AudioFadeTests(SimpleTestCase):
    def constant_audio(self):
        clip = AudioClip(
            lambda t: np.ones((len(t), 2)) if isinstance(t, np.ndarray) else np.ones(2),
            duration=4, fps=44100,
        )
        self.addCleanup(clip.close)
        return clip

    def test_disabled_fades_preserve_samples_including_the_first_frame(self):
        original = self.constant_audio()
        result = apply_audio_fades(original)
        self.assertIs(result, original)
        np.testing.assert_array_equal(result.get_frame(np.array([0, 1, 3.9])), np.ones((3, 2)))

    def test_oversized_fades_leave_the_middle_at_full_volume(self):
        result = apply_audio_fades(self.constant_audio(), fade_in=10, fade_out=10)
        times = np.array([0, 0.5, 2, 3.5, 3.9])
        expected = np.repeat(np.array([0, 0.25, 1, 0.25, 0.05])[:, None], 2, axis=1)
        np.testing.assert_allclose(result.get_frame(times), expected)
        np.testing.assert_allclose(result.get_frame(0.5), [0.25, 0.25])
