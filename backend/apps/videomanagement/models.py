from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from random import randint
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import IntegrityError, models, router, transaction
from django.utils import timezone
from django_lifecycle import AFTER_UPDATE, LifecycleModelMixin, hook
from django_lifecycle.conditions import WhenFieldValueChangesTo
from django_resized import ResizedImageField

from apps.apikeysmanagement.models import Provider
from apps.usermanagement.models import Notification
from apps.usermanagement.tasks import send_email

from .querysets import (
    ActiveSceneManager,
    AIUsageQuerySet,
    SceneQuerySet,
    VideoQuerySet,
    VoiceModelQuerySet,
)
from .utils.file_utils import check_if_video, stored_file_exists
from .utils.timing import file_timing
from .video_formats import (
    DEFAULT_VIDEO_FORMAT,
    DEFAULT_VIDEO_PLATFORM,
    VIDEO_FORMAT_CHOICES,
    VIDEO_PLATFORM_CHOICES,
)

logger = logging.getLogger(__name__)


def caption_upload_path(instance, filename):
    return f"media/captions/{instance.pk}/source{Path(filename).suffix.lower()}"


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class NewsUpdate(UUIDModel, TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    title = models.CharField(max_length=200)
    content = models.TextField(help_text="Plain text. Use blank lines between paragraphs.")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    published_at = models.DateTimeField(
        default=timezone.now,
        help_text="Published entries become visible on this date. Future dates schedule an update.",
    )

    class Meta:
        ordering = ["-published_at", "-id"]
        indexes = [models.Index(fields=["status", "published_at"], name="news_publication_idx")]

    def __str__(self):
        return self.title


class AbstractModel(UUIDModel):
    created_by = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, blank=True, null=True
    )
    objects = models.Manager()

    class Meta:
        abstract = True


class CaptionProjectStatus(models.TextChoices):
    QUEUED = "QUEUED", "QUEUED"
    TRANSCRIBING = "TRANSCRIBING", "TRANSCRIBING"
    READY = "READY", "READY"
    RENDER_QUEUED = "RENDER_QUEUED", "RENDER_QUEUED"
    RENDERING = "RENDERING", "RENDERING"
    COMPLETED = "COMPLETED", "COMPLETED"
    FAILED = "FAILED", "FAILED"


class CaptionProject(UUIDModel, TimestampedModel):
    created_by = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    source = models.FileField(upload_to=caption_upload_path, max_length=255)
    preview = models.FileField(blank=True, max_length=255)
    output = models.FileField(blank=True, max_length=255)
    words = models.JSONField(default=list)
    style = models.JSONField(default=dict)
    duration = models.FloatField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=CaptionProjectStatus.choices,
        default=CaptionProjectStatus.QUEUED,
    )
    error = models.CharField(max_length=300, blank=True)
    job_id = models.UUIDField(null=True, editable=False)

    class Meta:
        ordering = ["-created_at"]


class AIUsage(models.Model):
    """One completed provider request; never stores prompts or credentials."""

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
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
    objects = AIUsageQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"], name="ai_usage_user_date")
        ]


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


class TransitionStyle(models.TextChoices):
    DEFAULT = "DEFAULT", "Video default"
    FADE = "FADE", "Fade"
    CUT = "CUT", "Cut"
    DISSOLVE = "DISSOLVE", "Cross dissolve"


class VoiceModelType(models.TextChoices):
    API = "API", "Api"
    CUSTOM_API = "CUSTOM_API", "Custom Api"


class VideoStatus(models.TextChoices):
    GENERATION = "GENERATION", "GENERATION"
    REVIEW = "REVIEW", "REVIEW"
    READY = "READY", "READY"
    RENDERING = "RENDERING", "RENDERING"
    COMPLETED = "COMPLETED", "COMPLETED"
    FAILED = "FAILED", "FAILED"


class ImageMode(models.TextChoices):
    AI = "AI", "AI"
    WEB = "WEB", "WEB"


class VideoType(models.TextChoices):
    AI = "AI", "AI"
    MANUAL = "MANUAL", "Manual"


IN_FLIGHT_STATUSES = (VideoStatus.GENERATION, VideoStatus.RENDERING)
RENDERABLE_STATUSES = (
    VideoStatus.READY,
    VideoStatus.COMPLETED,
    VideoStatus.RENDERING,
)

VOICE_PROVIDERS = (Provider.OPENAI, Provider.ELEVENLABS, Provider.SIXTYDB)

GPT_MODEL_CHOICES = [(model, model) for model in settings.ACCEPTED_MODELS]
ACCOUNT_SCOPED_VOICE_PROVIDERS = (Provider.ELEVENLABS, Provider.SIXTYDB)


def default_video_settings() -> dict:
    return {
        "subtitles": False,
        "avatar_position": "right,top",
        "video_format": DEFAULT_VIDEO_FORMAT,
        "platform": DEFAULT_VIDEO_PLATFORM,
    }


class TemplatePrompt(AbstractModel):
    ai_scene_editing = models.BooleanField(default=False)
    title = models.CharField(max_length=50, blank=False)
    scene_count = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(60)]
    )

    # Preset generation fields with choices
    message = models.TextField(max_length=2000, blank=True, default="")
    voice_id = models.CharField(max_length=36, blank=True, null=True, default=None)
    gpt_model = models.CharField(
        max_length=50,
        choices=GPT_MODEL_CHOICES,
        default=settings.DEFAULT_GPT_MODEL,
        blank=True,
    )
    image_mode = models.CharField(
        max_length=20, choices=ImageMode.choices, default=ImageMode.WEB, blank=True
    )
    style = models.CharField(max_length=20, default="vivid", blank=True)
    music = models.CharField(max_length=500, blank=True, default="")
    target_audience = models.CharField(max_length=30, blank=True, default="")
    subtitles = models.BooleanField(default=False)
    narration = models.BooleanField(default=True)
    provider = models.CharField(max_length=50, blank=True, null=True, default=None)
    avatar_position = models.CharField(max_length=50, blank=True, default="right,top")
    video_format = models.CharField(
        max_length=12,
        choices=VIDEO_FORMAT_CHOICES,
        default=DEFAULT_VIDEO_FORMAT,
    )
    platform = models.CharField(
        max_length=12,
        choices=VIDEO_PLATFORM_CHOICES,
        default=DEFAULT_VIDEO_PLATFORM,
    )
    genre = models.CharField(max_length=50, blank=True, default="")

    # Foreign Key Relations
    avatar_selection = models.ForeignKey(
        "Avatar",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="template_prompts",
    )
    intro = models.ForeignKey(
        "Intro",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="template_prompts",
    )
    outro = models.ForeignKey(
        "Outro",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="template_prompts",
    )

    objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["created_by", "title"], name="unique_template_title_per_owner"
            )
        ]

    def __str__(self):
        return self.title


class Music(AbstractModel):
    name = models.CharField(max_length=140, blank=False)
    file = models.FileField(upload_to="media/music", blank=False)
    objects = models.Manager()

    def __str__(self):
        return self.name


class UserPrompt(UUIDModel):
    prompt = models.TextField(blank=False)
    objects = models.Manager()

    def __str__(self):
        return f"{self.id}"


class Scene(UUIDModel):
    archived_at = models.DateTimeField(
        null=True, blank=True, editable=False, db_index=True
    )
    archived_position = models.PositiveIntegerField(
        null=True, blank=True, editable=False
    )
    caption_alignment = models.JSONField(default=dict, blank=True)
    overlays = models.JSONField(default=list, blank=True)
    overlay_logo = models.ImageField(upload_to="media/overlays/%Y/%m/%d", blank=True)
    voiceover = models.FileField(
        upload_to="media/voiceovers", blank=True, max_length=2000
    )
    audio_settings = models.JSONField(default=dict, blank=True)

    motion_style = models.CharField(
        max_length=10, choices=MotionStyle.choices, default=MotionStyle.NONE
    )
    motion_intensity = models.CharField(
        max_length=6, choices=MotionIntensity.choices, default=MotionIntensity.SUBTLE
    )
    pause_after = models.FloatField(default=0)
    transition_after = models.CharField(
        max_length=8, choices=TransitionStyle.choices, default=TransitionStyle.DEFAULT
    )
    transition_duration = models.FloatField(null=True, blank=True, default=None)
    position = models.PositiveIntegerField(default=None, editable=False)
    created_at = models.DateTimeField(
        default=timezone.now, editable=False, db_index=True
    )

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["video", "position"], name="unique_scene_position"
            ),
        ]

    video = models.ForeignKey("Video", on_delete=models.CASCADE, related_name="scenes")
    file = models.FileField(
        upload_to="media/speech", blank=True, null=True, max_length=2000
    )
    text = models.TextField()
    is_last = models.BooleanField(default=True)
    objects = ActiveSceneManager()
    all_objects = SceneQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if self.position is not None:
            return super().save(*args, **kwargs)
        using = kwargs.get("using") or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            Video.objects.using(using).select_for_update().get(pk=self.video_id)
            last = (
                Scene.all_objects.using(using)
                .filter(video_id=self.video_id)
                .aggregate(last=models.Max("position"))["last"]
            )
            self.position = (last or 0) + 1
            return super().save(*args, **{**kwargs, "using": using})

    def __str__(self):
        return str(self.id)


class SceneImage(UUIDModel):
    asset = models.ForeignKey(
        "MediaAsset",
        null=True,
        blank=True,
        on_delete=models.RESTRICT,
        related_name="scene_visuals",
        editable=False,
    )

    created_at = models.DateTimeField(
        default=timezone.now, editable=False, db_index=True
    )

    class Meta:
        ordering = ["created_at"]

    scene = models.ForeignKey(
        Scene, on_delete=models.CASCADE, related_name="scene_images"
    )
    prompt = models.TextField(default="", blank=True, null=True)
    with_audio = models.BooleanField(default=False)
    objects = models.Manager()

    @property
    def file(self):
        """Rendering and API compatibility; the asset owns the actual file."""
        if hasattr(self, "_pending_asset"):
            return self._pending_asset.file
        return self.asset.file if self.asset_id else MediaAsset().file

    @file.setter
    def file(self, value):
        self._pending_asset = MediaAsset(file=value)

    def save(self, *args, **kwargs):
        pending = getattr(self, "_pending_asset", None)
        if pending is None:
            return super().save(*args, **kwargs)
        self._uploaded_file = None
        try:
            with transaction.atomic():
                self.asset = MediaAsset.from_scene_file(self.scene, pending.file)
                self._uploaded_file = getattr(self.asset, "_uploaded_file", None)
                result = super().save(*args, **kwargs)
            del self._pending_asset
            return result
        except Exception:
            self.discard_upload()
            raise

    def discard_upload(self):
        """Remove a newly written file only when its asset transaction rolled back."""
        file = getattr(self, "_uploaded_file", None)
        if file and not MediaAsset.objects.filter(file=file.name).exists():
            file.storage.delete(file.name)


class VoiceModel(AbstractModel):
    name = models.CharField(max_length=200, blank=True)
    provider = models.CharField(max_length=100, blank=True)
    type = models.CharField(max_length=10, choices=VoiceModelType.choices)
    sample = models.URLField(blank=True, null=True, max_length=1000)
    path = models.CharField(max_length=255, blank=False)
    is_cloned = models.BooleanField(default=False)
    clone_key_source = models.CharField(max_length=10, blank=True)
    clone_key_fingerprint = models.CharField(max_length=64, blank=True)
    consented_at = models.DateTimeField(null=True, blank=True)
    requires_verification = models.BooleanField(default=False)
    objects = VoiceModelQuerySet.as_manager()

    def __str__(self):
        return self.name

    @staticmethod
    def select_voice(user=None) -> VoiceModel:
        voice = VoiceModel.objects.available_to(user)
        count = voice.count()
        if count == 0:
            return None

        return voice[randint(0, count - 1)]


class Avatar(AbstractModel):
    name = models.CharField(max_length=100, default="Natasha")
    gender = models.CharField(max_length=10)
    file = ResizedImageField(
        size=[256, 256],
        quality=75,
        upload_to="media/other/avatars",
        force_format="jpeg",
    )
    voice = models.ForeignKey(
        VoiceModel, null=True, on_delete=models.SET_NULL, db_constraint=False
    )
    objects = models.Manager()

    def __str__(self):
        return self.name


class Intro(AbstractModel):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to="media/other/intros")
    objects = models.Manager()


class Outro(AbstractModel):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to="media/other/outros")
    objects = models.Manager()


class Video(LifecycleModelMixin, AbstractModel, TimestampedModel):
    created_at = models.DateTimeField(
        default=timezone.now, editable=False, db_index=True
    )

    class Meta:
        ordering = ["created_at"]

    reference_image = models.ImageField(
        upload_to="media/references/%Y/%m/%d", blank=True
    )
    cover = models.ImageField(upload_to="media/covers/%Y/%m/%d", blank=True)
    thumbnail = models.ImageField(upload_to="media/thumbnails/%Y/%m/%d", blank=True)
    cover_settings = models.JSONField(default=dict, blank=True)
    is_favorite = models.BooleanField(default=False)
    tags = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="", max_length=10000)
    title = models.CharField(max_length=50, blank=False)
    url = models.URLField(blank=True)
    gpt_answer = models.JSONField(blank=True, null=True)
    prompt = models.ForeignKey(
        UserPrompt, related_name="video_prompt", on_delete=models.CASCADE
    )
    genre = models.CharField(blank=True, null=True, max_length=20)
    output = models.FileField(
        upload_to="media/output", blank=True, null=True, max_length=2000
    )
    dir_name = models.TextField(default="")
    voice_model = models.ForeignKey(
        VoiceModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_constraint=False,
    )
    avatar = models.ForeignKey(
        Avatar,
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        blank=True,
        db_constraint=False,
    )
    status = models.CharField(
        max_length=20, choices=VideoStatus.choices, default=VideoStatus.RENDERING
    )
    music = models.ForeignKey(Music, blank=True, null=True, on_delete=models.SET_NULL)
    intro = models.ForeignKey(Intro, blank=True, null=True, on_delete=models.SET_NULL)
    outro = models.ForeignKey(Outro, blank=True, null=True, on_delete=models.SET_NULL)
    video_type = models.CharField(
        max_length=20, default=VideoType.AI, choices=VideoType.choices
    )
    mode = models.CharField(
        max_length=30, choices=ImageMode.choices, default=ImageMode.WEB, null=True
    )
    settings = models.JSONField(
        null=True,
        blank=True,
        default=default_video_settings,
    )

    objects = VideoQuerySet.as_manager()

    def toggle_favorite(self):
        self.is_favorite = not self.is_favorite
        self.save(update_fields=["is_favorite"])

    def __str__(self):
        return f"{self.title}"

    @hook(
        AFTER_UPDATE,
        on_commit=True,
        condition=WhenFieldValueChangesTo("status", VideoStatus.COMPLETED),
    )
    def send_video_completed_email(self):
        self.tell_owner(
            "Video Completed",
            f"Your video {self.title} has been completed. "
            f"You can download it from {self.url}",
        )

    @hook(
        AFTER_UPDATE,
        on_commit=True,
        condition=WhenFieldValueChangesTo("status", VideoStatus.FAILED),
    )
    def send_video_failed_email(self):
        self.tell_owner(
            "Video Failed", f"Your video {self.title} has failed. Please try again."
        )

    def tell_owner(self, subject: str, message: str) -> None:
        if not self.created_by:
            return

        Notification.objects.create(
            user=self.created_by,
            title=subject,
            message=message,
            link=f"/videos/{self.pk}/",
        )
        send_email.delay(name=subject, email=self.created_by.email, text=message)


class MediaAsset(AbstractModel):
    checksum = models.CharField(max_length=64, null=True, blank=True, editable=False)
    source_video = models.ForeignKey(
        Video,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="library_assets",
        editable=False,
    )

    class Kind(models.TextChoices):
        IMAGE = "IMAGE", "Image"
        VIDEO = "VIDEO", "Video"
        AUDIO = "AUDIO", "Audio"

    title = models.CharField(max_length=100)
    file = models.FileField(upload_to="media/library/%Y/%m/%d", max_length=2000)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    tags = models.JSONField(default=list, blank=True)
    duration = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=("created_by", "checksum"), name="unique_owner_visual_checksum"
            )
        ]

    @classmethod
    def from_scene_file(cls, scene, file):
        """Register an existing scene file or save its upload directly as an asset."""
        if not file:
            return None
        kind = cls.Kind.VIDEO if check_if_video(file.name) else cls.Kind.IMAGE
        defaults = {
            "title": f"{scene.video.title} · Scene {scene.position}"[:100],
            "tags": ["scene video" if kind == cls.Kind.VIDEO else "scene image"],
            "kind": kind,
            "source_video": scene.video,
        }
        if not file._committed:
            return cls.from_visual(
                user=scene.video.created_by, upload=file.file, **defaults
            )
        existing = cls.objects.filter(
            created_by=scene.video.created_by, file=file.name
        ).first()
        if existing:
            return existing
        return cls.objects.create(
            created_by=scene.video.created_by,
            file=file.name,
            duration=file_timing(file).get("duration")
            if kind == cls.Kind.VIDEO
            else None,
            **defaults,
        )

    @classmethod
    def from_visual(
        cls, *, user, upload, title, tags, kind, duration=None, source_video=None
    ):
        """Save an uploaded visual once, reusing identical assets for this owner."""
        digest = hashlib.sha256()
        upload.seek(0)
        for chunk in upload.chunks():
            digest.update(chunk)
        upload.seek(0)
        checksum = digest.hexdigest()
        matches = cls.objects.filter(created_by=user, checksum=checksum)
        existing = matches.first()
        if existing and stored_file_exists(existing.file):
            return existing
        asset = existing or cls(
            created_by=user,
            checksum=checksum,
            title=title[:100],
            tags=tags,
            kind=kind,
            duration=duration,
            source_video=source_video,
        )
        name = f"{uuid4().hex}{Path(upload.name).suffix.lower()}"
        asset.file.save(name, upload, save=False)
        saved_name = asset.file.name
        try:
            with transaction.atomic():
                if kind == cls.Kind.VIDEO and duration is None:
                    asset.duration = file_timing(asset.file).get("duration")
                asset.save()
        except IntegrityError:
            asset.file.storage.delete(saved_name)
            # A concurrent request may have archived the same bytes first.
            winner = matches.first()
            if winner:
                return winner
            raise
        except Exception:
            asset.file.storage.delete(saved_name)
            raise
        finally:
            upload.seek(0)
        asset._uploaded_file = asset.file
        return asset
