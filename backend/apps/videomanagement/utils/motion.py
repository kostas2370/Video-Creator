"""Image motion geometry shared by preview metadata and rendering."""

MOTION_STYLES = (
    "NONE",
    "AUTO",
    "ZOOM_IN",
    "ZOOM_OUT",
    "PAN_LEFT",
    "PAN_RIGHT",
    "PAN_UP",
    "PAN_DOWN",
)
MOTION_INTENSITIES = ("SUBTLE", "MEDIUM", "STRONG")
AMOUNTS = {"SUBTLE": 0.06, "MEDIUM": 0.12, "STRONG": 0.20}


def resolved_motion(scene):
    style = scene.motion_style
    if style == "AUTO":
        style = MOTION_STYLES[2:][scene.pk.int % 6]
    return style


def motion_geometry(style, intensity, progress):
    """Return scale and translation as fractions of the output canvas."""
    progress = min(1, max(0, progress))
    amount = AMOUNTS.get(intensity, AMOUNTS["SUBTLE"])
    if style == "ZOOM_IN":
        return 1 + amount * progress, 0, 0
    if style == "ZOOM_OUT":
        return 1 + amount * (1 - progress), 0, 0
    travel = amount * (progress - 0.5)
    if style == "PAN_LEFT":
        return 1 + amount, -travel, 0
    if style == "PAN_RIGHT":
        return 1 + amount, travel, 0
    if style == "PAN_UP":
        return 1 + amount, 0, -travel
    if style == "PAN_DOWN":
        return 1 + amount, 0, travel
    return 1, 0, 0
