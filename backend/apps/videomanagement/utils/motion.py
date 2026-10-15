"""Image motion geometry shared by preview metadata and rendering."""

from ..models import MotionIntensity, MotionStyle

MOTION_STYLES = tuple(MotionStyle.values)
AMOUNTS = {
    MotionIntensity.SUBTLE: 0.06,
    MotionIntensity.MEDIUM: 0.12,
    MotionIntensity.STRONG: 0.20,
}


def resolved_motion(scene):
    style = scene.motion_style
    if style == MotionStyle.AUTO:
        style = MOTION_STYLES[2:][scene.pk.int % 6]
    return style
