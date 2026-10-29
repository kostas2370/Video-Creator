from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import models


def source_path(instance, filename):
    return f"media/clips/{instance.pk}/source{Path(filename).suffix.lower()}"


class ClipProject(models.Model):
    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        TRANSCRIBING = "TRANSCRIBING", "Transcribing"
        ANALYZING = "ANALYZING", "Finding highlights"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Needs attention"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    source = models.FileField(upload_to=source_path, max_length=255)
    preview = models.FileField(blank=True, max_length=255)
    duration = models.FloatField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    words = models.JSONField(default=list)
    transcript_parts = models.JSONField(default=list)
    extraction_prompt = models.TextField(max_length=2000, blank=True, null=True)
    clip_count = models.PositiveSmallIntegerField(default=5)
    min_duration = models.PositiveSmallIntegerField(default=30)
    max_duration = models.PositiveSmallIntegerField(default=60)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.QUEUED
    )
    error = models.CharField(max_length=300, blank=True)
    job_id = models.UUIDField(null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class Clip(models.Model):
    class Status(models.TextChoices):
        READY = "READY", "Ready"
        QUEUED = "QUEUED", "Queued"
        RENDERING = "RENDERING", "Exporting"
        COMPLETED = "COMPLETED", "Export ready"
        FAILED = "FAILED", "Needs attention"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
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
        choices=[("CROP", "Crop to portrait"), ("FIT", "Blurred background")],
        default="FIT",
    )
    crop_position = models.FloatField(default=50)
    captions = models.BooleanField(default=True)
    words = models.JSONField(default=list)
    style = models.JSONField(default=dict)
    output = models.FileField(blank=True, max_length=255)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.READY
    )
    error = models.CharField(max_length=300, blank=True)
    job_id = models.UUIDField(null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end__gt=models.F("start")),
                name="clip_positive_duration",
            )
        ]
