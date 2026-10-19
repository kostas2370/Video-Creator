import subprocess

import numpy as np
from django.test import SimpleTestCase

from ...utils.composer.effects import audio_fade_filters


class AudioFadeTests(SimpleTestCase):
    def samples(self, fade_in=0, fade_out=0):
        filters = audio_fade_filters(4, fade_in=fade_in, fade_out=fade_out)
        command = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "aevalsrc=1:s=8000:d=4"]
        if filters:
            command.extend(["-af", ",".join(filters)])
        command.extend(["-f", "f32le", "pipe:1"])
        return np.frombuffer(subprocess.check_output(command), dtype="<f4")

    def test_disabled_fades_preserve_samples_including_the_first_frame(self):
        samples = self.samples()
        np.testing.assert_array_equal(samples[[0, 8000, 31200]], [1, 1, 1])

    def test_oversized_fades_leave_the_middle_at_full_volume(self):
        samples = self.samples(fade_in=10, fade_out=10)
        np.testing.assert_allclose(samples[[0, 4000, 16000, 28000, 31200]], [0, 0.25, 1, 0.25, 0.05])
