from pathlib import Path

from django.conf import settings
from django.db import models

from apps.videomanagement.models import TimestampedModel, UUIDModel

from .choices import ClipLayout, ClipProjectStatus, ClipStatus
from .storage import clip_storage


def source_path(instance, filename):
    return f"media/clips/{instance.pk}/source{Path(filename).suffix.lower()}"


class ClipProject(UUIDModel, TimestampedModel):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    source = models.FileField(
        upload_to=source_path, max_length=255, storage=clip_storage, blank=True
    )
    preview = models.FileField(blank=True, max_length=255, storage=clip_storage)
    youtube_url = models.URLField(max_length=500, blank=True)
    duration = models.FloatField(default=0)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    words = models.JSONField(default=list)
    transcript_parts = models.JSONField(default=list)
    extraction_prompt = models.TextField(max_length=2000, blank=True, null=True)
    clip_count = models.PositiveSmallIntegerField(default=5)
    min_duration = models.PositiveSmallIntegerField(default=30)
    max_duration = models.PositiveSmallIntegerField(default=60)
    status = models.CharField(
        max_length=20,
        choices=ClipProjectStatus.choices,
        default=ClipProjectStatus.QUEUED,
    )
    error = models.CharField(max_length=300, blank=True)
    job_id = models.UUIDField(null=True, editable=False)

    class Meta:
        ordering = ["-created_at"]


class Clip(UUIDModel, TimestampedModel):
    project = models.ForeignKey(
        ClipProject, related_name="clips", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=100)
    reason = models.CharField(max_length=400, blank=True)
    hashtags = models.JSONField(default=list)
    start = models.FloatField()
    end = models.FloatField()
    layout = models.CharField(
        max_length=10,
        choices=ClipLayout.choices,
        default=ClipLayout.FIT,
    )
    crop_position = models.FloatField(default=50)
    captions = models.BooleanField(default=True)
    words = models.JSONField(default=list)
    style = models.JSONField(default=dict)
    output = models.FileField(blank=True, max_length=255, storage=clip_storage)
    status = models.CharField(
        max_length=20, choices=ClipStatus.choices, default=ClipStatus.READY
    )
    error = models.CharField(max_length=300, blank=True)
    job_id = models.UUIDField(null=True, editable=False)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end__gt=models.F("start")),
                name="clip_positive_duration",
            )
        ]
