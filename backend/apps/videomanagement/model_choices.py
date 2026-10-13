from django.db import models


class MotionStyle(models.TextChoices):
    NONE = "NONE", "None"
    AUTO = "AUTO", "Auto"
    ZOOM_IN = "ZOOM_IN", "Zoom In"
    ZOOM_OUT = "ZOOM_OUT", "Zoom Out"
    PAN_LEFT = "PAN_LEFT", "Pan Left"
    PAN_RIGHT = "PAN_RIGHT", "Pan Right"
    PAN_UP = "PAN_UP", "Pan Up"
    PAN_DOWN = "PAN_DOWN", "Pan Down"


class MotionIntensity(models.TextChoices):
    SUBTLE = "SUBTLE", "Subtle"
    MEDIUM = "MEDIUM", "Medium"
    STRONG = "STRONG", "Strong"
