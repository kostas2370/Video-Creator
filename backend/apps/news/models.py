from django.db import models
from django.utils import timezone

from apps.common.models import TimestampedModel, UUIDModel


class NewsUpdate(UUIDModel, TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    title = models.CharField(max_length=200)
    content = models.TextField(
        help_text="Plain text. Use blank lines between paragraphs."
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    published_at = models.DateTimeField(
        default=timezone.now,
        help_text="Published entries become visible on this date. Future dates schedule an update.",
    )

    class Meta:
        ordering = ["-published_at", "-id"]
        indexes = [
            models.Index(fields=["status", "published_at"], name="news_publication_idx")
        ]

    def __str__(self):
        return self.title
