"""Animate a fitted still image, keeping the canvas size fixed."""

import numpy as np
from PIL import Image
from moviepy.editor import VideoClip

from ..motion import motion_geometry, resolved_motion


def animate_image(clip, scene):
    style = resolved_motion(scene)
    if style == "NONE":
        return clip
    image = Image.fromarray(clip.get_frame(0).astype(np.uint8))
    width, height = image.size
    end = max(0, clip.duration - 1 / 24)

    def frame(t):
        scale, x, y = motion_geometry(
            style, scene.motion_intensity, t / end if end else 1
        )
        left = width * (0.5 - (0.5 + x) / scale)
        top = height * (0.5 - (0.5 + y) / scale)
        return np.asarray(
            image.transform(
                (width, height),
                Image.Transform.AFFINE,
                (1 / scale, 0, left, 0, 1 / scale, top),
                resample=Image.Resampling.BICUBIC,
            )
        )

    return VideoClip(frame, duration=clip.duration)
