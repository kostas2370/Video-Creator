from django.db import models


class ClipProjectStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    DOWNLOADING = "DOWNLOADING", "Downloading YouTube video"
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


class ClipFocus(models.TextChoices):
    GENERAL = "general", "General highlights"
    FUNNY = "funny", "Funny moments"
    ADVICE = "advice", "Practical advice"
    STORIES = "stories", "Stories"
    DEBATE = "debate", "Debates and opinions"


class ClipSelectionMode(models.TextChoices):
    FAST = "fast", "Fast"
    BALANCED = "balanced", "Balanced"
    STRICT = "strict", "Strict"


PROJECT_BUSY = frozenset(
    {
        ClipProjectStatus.QUEUED,
        ClipProjectStatus.DOWNLOADING,
        ClipProjectStatus.TRANSCRIBING,
        ClipProjectStatus.ANALYZING,
    }
)
CLIP_BUSY = frozenset({ClipStatus.QUEUED, ClipStatus.RENDERING})
