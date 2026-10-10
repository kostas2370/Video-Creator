from __future__ import annotations
from uuid import UUID, uuid4
from django.db import models, router, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from random import randint
from typing import Union
from django_resized import ResizedImageField
from django.conf import settings
from django_lifecycle import LifecycleModelMixin, hook, AFTER_UPDATE
from django_lifecycle.conditions import WhenFieldValueChangesTo
from apps.apikeysmanagement.models import ApiKeys, Provider
from apps.usermanagement.models import Notification
from apps.usermanagement.tasks import send_email
from .video_formats import (
    DEFAULT_VIDEO_FORMAT,
    DEFAULT_VIDEO_PLATFORM,
    VIDEO_FORMAT_CHOICES,
    VIDEO_PLATFORM_CHOICES,
)
import logging

logger = logging.getLogger(__name__)


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


class AbstractModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    created_by = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, blank=True, null=True
    )
    objects = models.Manager()

    class Meta:
        abstract = True


class TemplatePrompt(AbstractModel):
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
    background = models.ForeignKey(
        "Background",
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


class UserPrompt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    prompt = models.TextField(blank=False)
    objects = models.Manager()

    def __str__(self):
        return f"{self.id}"


class Scene(models.Model):
    position = models.PositiveIntegerField(default=None, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["video", "position"], name="unique_scene_position"),
        ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    video = models.ForeignKey("Video", on_delete=models.CASCADE, related_name="scenes")
    file = models.FileField(
        upload_to="media/speech", blank=True, null=True, max_length=2000
    )
    text = models.TextField()
    is_last = models.BooleanField(default=True)
    objects = models.Manager()

    def save(self, *args, **kwargs):
        if self.position is not None:
            return super().save(*args, **kwargs)
        using = kwargs.get("using") or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            Video.objects.using(using).select_for_update().get(pk=self.video_id)
            last = Scene.objects.using(using).filter(video_id=self.video_id).aggregate(
                last=models.Max("position")
            )["last"]
            self.position = (last or 0) + 1
            return super().save(*args, **{**kwargs, "using": using})

    def __str__(self):
        return str(self.id)


class SceneImage(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)

    class Meta:
        ordering = ["created_at"]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    scene = models.ForeignKey(
        Scene, on_delete=models.CASCADE, related_name="scene_images"
    )
    file = models.FileField(
        upload_to="media/images", null=True, blank=True, max_length=2000
    )
    prompt = models.TextField(default="", blank=True, null=True)
    with_audio = models.BooleanField(default=False)
    objects = models.Manager()


class VoiceModel(AbstractModel):
    name = models.CharField(max_length=200, blank=True)
    provider = models.CharField(max_length=100, blank=True)
    type = models.CharField(max_length=10, choices=VoiceModelType.choices)
    sample = models.URLField(blank=True, null=True, max_length=1000)
    path = models.CharField(max_length=255, blank=False)
    objects = models.Manager()

    def __str__(self):
        return self.name

    @staticmethod
    def available_to(user) -> models.QuerySet:
        playable = [
            provider for provider in VOICE_PROVIDERS if ApiKeys.key_for(user, provider)
        ]
        spending_own_keys = (
            user is not None
            and getattr(user, "is_authenticated", False)
            and not user.use_service_api_keys
        )
        shared = models.Q(created_by=None)
        if spending_own_keys:
            scope = (
                shared & ~models.Q(provider__in=ACCOUNT_SCOPED_VOICE_PROVIDERS)
            ) | models.Q(created_by=user)
        else:
            scope = shared

        valid_providers = models.Q(provider__in=playable) | (
            models.Q(type=VoiceModelType.CUSTOM_API) & models.Q(created_by=user)
        )

        return VoiceModel.objects.filter(scope & valid_providers)

    @staticmethod
    def select_voice(user=None) -> VoiceModel:
        voice = VoiceModel.available_to(user)
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

    @staticmethod
    def select_avatar(
        selected: str = "random", voice_model: VoiceModel = None, user=None
    ) -> Union[Avatar, None]:
        if user is None:
            return None
        avatars = Avatar.objects.filter(created_by=user)
        if selected == "random":
            if voice_model is not None:
                avatars = avatars.filter(voice=voice_model)
            count = avatars.count()
            return avatars[randint(0, count - 1)] if count else None
        if isinstance(selected, (str, UUID)):
            try:
                return avatars.filter(id=selected).first()
            except (ValidationError, ValueError):
                return None
        return None


class Background(AbstractModel):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to="media/other/backgrounds")
    color = models.CharField(max_length=30)
    image_pos_top = models.IntegerField()
    image_pos_left = models.IntegerField()
    avatar_pos_top = models.IntegerField()
    avatar_pos_left = models.IntegerField()
    through = models.IntegerField(default=6)
    objects = models.Manager()

    def __str__(self):
        return self.name

    @staticmethod
    def select_background() -> Background:
        back = Background.objects.all()

        return back[randint(0, back.count() - 1)] if back.exists() else None


class Intro(AbstractModel):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to="media/other/intros")
    objects = models.Manager()


class Outro(AbstractModel):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to="media/other/outros")
    objects = models.Manager()


class Video(LifecycleModelMixin, AbstractModel):
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)

    class Meta:
        ordering = ["created_at"]

    reference_image = models.ImageField(upload_to="media/references/%Y/%m/%d", blank=True)
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
    updated_at = models.DateTimeField(auto_now=True)
    music = models.ForeignKey(Music, blank=True, null=True, on_delete=models.SET_NULL)
    background = models.ForeignKey(
        Background, blank=True, null=True, on_delete=models.SET_NULL
    )
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

    objects = models.Manager()

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
