from django.db import models


class ClipProjectStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    TRANSCRIBING = "TRANSCRIBING", "Transcribing"
    ANALYZING = "ANALYZING", "Finding highlights"
    READY = "READY", "Ready"
    FAILED = "FAILED", "Needs attention"


class ClipStatus(models.TextChoices):
    READY = "READY", "Ready"
    QUEUED = "QUEUED", "Queued"
    RENDERING = "RENDERING", "Exporting"
    COMPLETED = "COMPLETED", "Export ready"
    FAILED = "FAILED", "Needs attention"


class ClipLayout(models.TextChoices):
    CROP = "CROP", "Crop to portrait"
    FIT = "FIT", "Blurred background"


PROJECT_BUSY = frozenset(
    {
        ClipProjectStatus.QUEUED,
        ClipProjectStatus.TRANSCRIBING,
        ClipProjectStatus.ANALYZING,
    }
)
CLIP_BUSY = frozenset({ClipStatus.QUEUED, ClipStatus.RENDERING})
