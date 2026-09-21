from __future__ import annotations
from django.db import models
from django.contrib.auth import get_user_model
from random import randint
from typing import Union
from django_resized import ResizedImageField
from django.conf import settings
from django_lifecycle import LifecycleModelMixin, hook, AFTER_UPDATE
from django_lifecycle.conditions import WhenFieldValueChangesTo
from apps.apikeysmanagement.models import ApiKeys, Provider
from apps.usermanagement.tasks import send_email

MODEL_TYPE_CHOICES = (("API", "Api"),)

VOICE_PROVIDER_KEYS = {
    "open_ai": Provider.OPENAI,
    "eleven_labs": Provider.ELEVENLABS,
    "60db": Provider.SIXTYDB,
}

GPT_MODEL_CHOICES = [(model, model) for model in settings.ACCEPTED_MODELS]
ACCOUNT_SCOPED_VOICE_PROVIDERS = ("eleven_labs", "60db")

VIDEO_STATUS = (
    ("GENERATION", "GENERATION"),
    ("READY", "READY"),
    ("RENDERING", "RENDERING"),
    ("COMPLETED", "COMPLETED"),
    ("FAILED", "FAILED"),
)


IMAGE_MODE = (("AI", "AI"), ("WEB", "WEB"))

VIDEO_TYPE = (("AI", "AI"), ("TWITCH", "TWITCH"))


class AbstractModel(models.Model):
    created_by = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, blank=True, null=True
    )
    objects = models.Manager()

    class Meta:
        abstract = True


class TemplatePrompt(AbstractModel):
    title = models.CharField(max_length=50, unique=True, blank=False)

    # Preset generation fields with choices
    message = models.TextField(max_length=2000, blank=True, default="")
    voice_id = models.CharField(max_length=20, blank=True, null=True, default=None)
    gpt_model = models.CharField(
        max_length=50,
        choices=GPT_MODEL_CHOICES,
        default=settings.DEFAULT_GPT_MODEL,
        blank=True,
    )
    image_mode = models.CharField(
        max_length=20, choices=IMAGE_MODE, default="WEB", blank=True
    )
    style = models.CharField(max_length=20, default="vivid", blank=True)
    music = models.CharField(max_length=500, blank=True, default="")
    target_audience = models.CharField(max_length=30, blank=True, default="")
    subtitles = models.BooleanField(default=False)
    narration = models.BooleanField(default=True)
    provider = models.CharField(max_length=50, blank=True, null=True, default=None)
    avatar_position = models.CharField(max_length=50, blank=True, default="right,top")
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

    def __str__(self):
        return self.title


class Music(AbstractModel):
    name = models.CharField(max_length=140, blank=False)
    file = models.FileField(upload_to="media/music", blank=False)
    objects = models.Manager()

    def __str__(self):
        return self.name


class UserPrompt(models.Model):
    prompt = models.TextField(blank=False)
    objects = models.Manager()

    def __str__(self):
        return f"{self.id}"


class Scene(models.Model):
    prompt = models.ForeignKey(
        UserPrompt, on_delete=models.CASCADE, related_name="scenes"
    )
    file = models.FileField(
        upload_to="media/speech", blank=True, null=True, max_length=2000
    )
    text = models.TextField()
    is_last = models.BooleanField(default=True)
    objects = models.Manager()

    def __str__(self):
        return str(self.id)


class SceneImage(models.Model):
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
    type = models.CharField(max_length=10, choices=MODEL_TYPE_CHOICES)
    sample = models.URLField(blank=True, null=True, max_length=1000)
    path = models.CharField(max_length=255, blank=False)
    objects = models.Manager()

    def __str__(self):
        return self.name

    @staticmethod
    def available_to(user) -> models.QuerySet:
        playable = [
            provider
            for provider, key in VOICE_PROVIDER_KEYS.items()
            if ApiKeys.key_for(user, key)
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

        return VoiceModel.objects.filter(scope, provider__in=playable)

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
        selected: str = "random", voice_model: VoiceModel = None
    ) -> Union[Avatar, None]:
        if selected == "random":
            if voice_model is None:
                avatars = Avatar.objects.all()
            else:
                avatars = Avatar.objects.filter(voice=voice_model)

            return avatars[randint(0, avatars.count() - 1)]

        if isinstance(selected, int):
            items = Avatar.objects.filter(id=selected)
            if items.count() == 1:
                return items.first()

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
    title = models.CharField(max_length=50, blank=False)
    url = models.URLField(blank=True)
    gpt_answer = models.TextField(blank=True, null=True)
    prompt = models.ForeignKey(
        UserPrompt, related_name="video_prompt", on_delete=models.CASCADE
    )
    genre = models.CharField(blank=True, null=True, max_length=20)
    output = models.FileField(
        upload_to="media/output", blank=True, null=True, max_length=2000
    )
    dir_name = models.TextField(default="")
    voice_model = models.ForeignKey(
        VoiceModel, on_delete=models.SET_NULL, null=True, default=1, db_constraint=False
    )
    avatar = models.ForeignKey(
        Avatar,
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        blank=True,
        db_constraint=False,
    )
    status = models.CharField(max_length=20, choices=VIDEO_STATUS, default="RENDERING")
    updated_at = models.DateTimeField(auto_now=True)
    music = models.ForeignKey(Music, blank=True, null=True, on_delete=models.SET_NULL)
    background = models.ForeignKey(
        Background, blank=True, null=True, on_delete=models.SET_NULL
    )
    intro = models.ForeignKey(Intro, blank=True, null=True, on_delete=models.SET_NULL)
    outro = models.ForeignKey(Outro, blank=True, null=True, on_delete=models.SET_NULL)
    video_type = models.CharField(max_length=20, default="AI", choices=VIDEO_TYPE)
    mode = models.CharField(max_length=30, choices=IMAGE_MODE, default="WEB", null=True)
    settings = models.JSONField(
        null=True,
        blank=True,
        default=dict(subtitles=False, avatar_position="right,top"),
    )

    objects = models.Manager()

    def __str__(self):
        return f"{self.title}"

    @hook(
        AFTER_UPDATE,
        on_commit=True,
        condition=WhenFieldValueChangesTo("status", "COMPLETED"),
    )
    def send_video_completed_email(self):
        message = f"Your video {self.title} has been completed. You can download it from {self.url}"
        send_email.delay(self.created_by.email, "Video Completed", message)

    @hook(
        AFTER_UPDATE,
        on_commit=True,
        condition=WhenFieldValueChangesTo("status", "FAILED"),
    )
    def send_video_failed_email(self):
        message = f"Your video {self.title} has failed. Please try again."
        send_email.delay(self.created_by.email, "Video Failed", message)
