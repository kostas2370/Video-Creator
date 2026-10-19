"""Compositing the talking head onto a finished render."""


import numpy as np
from django.test import SimpleTestCase
from PIL import Image

from vendor.sadtalker.src.utils.croper import Preprocesser


class FaceAlignmentTests(SimpleTestCase):
    def test_large_face_images_can_be_resized_with_current_pillow(self):
        landmarks = np.zeros((68, 2), dtype=float)
        landmarks[36:42] = (100, 100)
        landmarks[42:48] = (300, 100)
        landmarks[48] = (140, 260)
        landmarks[54] = (260, 260)
        preprocesser = Preprocesser.__new__(Preprocesser)

        with Image.new("RGB", (512, 512)) as image:
            size, crop, bounds = preprocesser.align_face(
                image, landmarks, output_size=64
            )

        self.assertEqual(size, (85, 85))
        self.assertGreater(crop[2], crop[0])
        self.assertGreater(crop[3], crop[1])
        self.assertGreater(bounds[2], bounds[0])
        self.assertGreater(bounds[3], bounds[1])
