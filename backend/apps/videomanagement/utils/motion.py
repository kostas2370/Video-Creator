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


def motion_geometry(style, intensity, progress):
    """Return scale and translation as fractions of the output canvas."""
    progress = min(1, max(0, progress))
    amount = AMOUNTS.get(intensity, AMOUNTS[MotionIntensity.SUBTLE])
    if style == MotionStyle.ZOOM_IN:
        return 1 + amount * progress, 0, 0
    if style == MotionStyle.ZOOM_OUT:
        return 1 + amount * (1 - progress), 0, 0
    travel = amount * (progress - 0.5)
    if style == MotionStyle.PAN_LEFT:
        return 1 + amount, -travel, 0
    if style == MotionStyle.PAN_RIGHT:
        return 1 + amount, travel, 0
    if style == MotionStyle.PAN_UP:
        return 1 + amount, 0, -travel
    if style == MotionStyle.PAN_DOWN:
        return 1 + amount, 0, travel
    return 1, 0, 0
