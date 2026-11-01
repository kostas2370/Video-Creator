from django.conf import settings
from django.db import models
from django.utils import timezone

from .querysets import AIUsageQuerySet


class AIUsage(models.Model):
    """One completed provider request; never stores prompts or credentials."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    service = models.CharField(
        max_length=10,
        choices=[
            ("text", "Text"),
            ("images", "Images"),
            ("tts", "Voice"),
            ("video", "Video"),
            ("stt", "Transcription"),
        ],
    )
    provider = models.CharField(max_length=100)
    model = models.CharField(max_length=100, blank=True)
    key_source = models.CharField(max_length=10)
    input_tokens = models.PositiveBigIntegerField(null=True)
    output_tokens = models.PositiveBigIntegerField(null=True)
    total_tokens = models.PositiveBigIntegerField(null=True)
    characters = models.PositiveBigIntegerField(default=0)
    images = models.PositiveIntegerField(default=0)
    seconds = models.PositiveIntegerField(default=0)
    video = models.ForeignKey(
        "videomanagement.Video",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_usage",
    )
    cost_usd = models.DecimalField(max_digits=16, decimal_places=8, null=True)
    cost_details = models.JSONField(default=dict, blank=True)
    objects = AIUsageQuerySet.as_manager()

    class Meta:
        db_table = "videomanagement_aiusage"
        indexes = [
            models.Index(fields=["user", "created_at"], name="ai_usage_user_date")
        ]


class GenerationEstimate(models.Model):
    video = models.OneToOneField("videomanagement.Video", on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    estimate = models.JSONField(default=dict)
