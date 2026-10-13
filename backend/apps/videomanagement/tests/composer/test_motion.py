from types import SimpleNamespace
from uuid import UUID

import numpy as np
from django.test import SimpleTestCase
from moviepy.editor import ImageClip

from ...utils.composer.motion import animate_image
from ...utils.composer.timing import hold_scene
from ...utils.motion import MOTION_STYLES, resolved_motion


class ImageMotionTests(SimpleTestCase):
    def test_all_movements_keep_the_canvas_filled_and_freeze_during_pause(self):
        pixels = np.full((60, 100, 3), 90, dtype=np.uint8)
        pixels[:, :, 0] = np.arange(100) + 20
        pixels[:, :, 1] = np.arange(60)[:, None] + 20
        for style in MOTION_STYLES[2:]:
            with self.subTest(style=style):
                source = ImageClip(pixels).set_duration(2)
                scene = SimpleNamespace(motion_style=style, motion_intensity="STRONG")
                moving = animate_image(source, scene)
                held, resources = hold_scene(moving, 1)
                try:
                    first, last = moving.get_frame(0), moving.get_frame(2 - 1 / 24)
                    self.assertFalse(np.array_equal(first, last))
                    for t in (0, 0.5, 1, 1.9, 2.5):
                        frame = held.get_frame(t)
                        self.assertEqual(frame.shape, (60, 100, 3))
                        self.assertGreater(frame.min(), 0)
                    np.testing.assert_array_equal(held.get_frame(2.5), last)
                    self.assertEqual(held.duration, 3)
                finally:
                    for clip in [source, moving, held, *resources]:
                        clip.close()

    def test_no_motion_preserves_original_clip(self):
        clip = ImageClip(np.ones((8, 8, 3), dtype=np.uint8)).set_duration(2)
        self.addCleanup(clip.close)
        self.assertIs(animate_image(clip, SimpleNamespace(motion_style="NONE")), clip)

    def test_auto_is_stable_when_scene_position_changes(self):
        scene = SimpleNamespace(pk=UUID(int=5), motion_style="AUTO", position=1)
        before = resolved_motion(scene)
        scene.position = 10
        self.assertEqual(resolved_motion(scene), before)
        self.assertIn(before, MOTION_STYLES[2:])
