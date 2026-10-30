from uuid import uuid4

from django.db import models
from django.utils import timezone


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TranscribedMediaModel(UUIDModel, TimestampedModel):
    title = models.CharField(max_length=100)
    words = models.JSONField(default=list)
    error = models.CharField(max_length=300, blank=True)
    job_id = models.UUIDField(null=True, editable=False)

    def mark_queued(self, status):
        self.job_id, self.status, self.error = uuid4(), status, ""
        self.save(update_fields=["job_id", "status", "error", "updated_at"])

    class Meta:
        abstract = True
