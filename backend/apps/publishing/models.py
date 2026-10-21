from uuid import uuid4

from django.conf import settings
from django.db import models
from encrypted_model_fields.fields import EncryptedTextField

from .storage import PrivateExportStorage


class Platform(models.TextChoices):
    YOUTUBE = "youtube", "YouTube"
    TIKTOK = "tiktok", "TikTok"
    INSTAGRAM = "instagram", "Instagram"


class SocialAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    platform = models.CharField(max_length=12, choices=Platform.choices)
    external_id = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField(blank=True, default="")
    expires_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "platform", "external_id"], name="unique_social_account")]


class OAuthAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    platform = models.CharField(max_length=12, choices=Platform.choices)
    state_hash = models.CharField(max_length=64, unique=True)
    browser_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    video = models.ForeignKey("videomanagement.Video", null=True, on_delete=models.SET_NULL)


class PublishJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Waiting to upload"
        UPLOADING = "UPLOADING", "Uploading"
        PROCESSING = "PROCESSING", "Platform processing"
        PUBLISHING = "PUBLISHING", "Publishing"
        PUBLISHED = "PUBLISHED", "Published"
        FAILED = "FAILED", "Failed"
        NEEDS_CHECK = "NEEDS_CHECK", "Check platform before trying again"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    video = models.ForeignKey("videomanagement.Video", on_delete=models.CASCADE)
    account = models.ForeignKey(SocialAccount, null=True, on_delete=models.SET_NULL)
    platform = models.CharField(max_length=12, choices=Platform.choices)
    account_name = models.CharField(max_length=255)
    request_id = models.UUIDField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    options = models.JSONField(default=dict)
    media = models.FileField(upload_to="exports/%Y/%m/%d", storage=PrivateExportStorage(), max_length=2000)
    thumbnail = models.FileField(upload_to="thumbnails/%Y/%m/%d", storage=PrivateExportStorage(), max_length=2000, blank=True)
    metadata = models.JSONField(default=dict)
    remote_id = models.CharField(max_length=255, blank=True)
    url = models.URLField(max_length=2000, blank=True)
    error = models.CharField(max_length=500, blank=True)
    warning = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "request_id"], name="unique_publish_request")]
