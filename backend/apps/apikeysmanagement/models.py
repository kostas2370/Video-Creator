from __future__ import annotations

import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
from django_lifecycle import (
    LifecycleModelMixin,
    hook,
    AFTER_UPDATE,
    AFTER_CREATE,
    AFTER_DELETE,
)
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class Provider(models.TextChoices):
    OPENAI = "OPENAI", "OpenAI"
    ANTHROPIC = "ANTHROPIC", "Anthropic"
    GEMINI = "GEMINI", "Google Gemini"
    ELEVENLABS = "ELEVENLABS", "ElevenLabs"
    SIXTYDB = "SIXTYDB", "60dB"
    STABLE_DIFFUSION = "STABLE_DIFFUSION", "Stable Diffusion"
    MIDJOURNEY = "MIDJOURNEY", "Midjourney"
    GOOGLE_SEARCH = "GOOGLE_SEARCH", "Google Custom Search"
    GOOGLE_SEARCH_ENGINE_ID = "GOOGLE_SEARCH_ENGINE_ID", "Google Search engine id"
    TWITCH_CLIENT = "TWITCH_CLIENT", "Twitch client id"
    TWITCH_SECRET = "TWITCH_SECRET", "Twitch client secret"


class AuthType(models.TextChoices):
    BEARER = "bearer", "Bearer Token"
    HEADER = "header", "Custom Header Key"
    BASIC = "basic", "Basic Auth"
    NONE = "none", "No Authentication"


VOICE_KEY_FIELDS = {
    "elevenlabs_key": Provider.ELEVENLABS,
    "sixtydb_key": Provider.SIXTYDB,
}


class ApiKeys(LifecycleModelMixin, models.Model):
    user = models.OneToOneField(
        get_user_model(), on_delete=models.CASCADE, related_name="api_keys"
    )

    openai_key = EncryptedCharField(max_length=255, blank=True, default="")
    anthropic_key = EncryptedCharField(max_length=255, blank=True, default="")
    gemini_key = EncryptedCharField(max_length=255, blank=True, default="")
    elevenlabs_key = EncryptedCharField(max_length=255, blank=True, default="")
    sixtydb_key = EncryptedCharField(max_length=255, blank=True, default="")
    diffusion_key = EncryptedCharField(max_length=255, blank=True, default="")
    midjourney_key = EncryptedCharField(max_length=255, blank=True, default="")
    google_search_key = EncryptedCharField(max_length=255, blank=True, default="")
    google_search_engine_id = EncryptedCharField(max_length=255, blank=True, default="")
    twitch_client_id = EncryptedCharField(max_length=255, blank=True, default="")
    twitch_client_secret = EncryptedCharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = "API keys"
        verbose_name_plural = "API keys"

    def __str__(self):
        return f"API keys for {self.user}"

    FIELDS = {
        Provider.OPENAI: ("openai_key", "OPEN_API_KEY"),
        Provider.ANTHROPIC: ("anthropic_key", "ANTHROPIC_API_KEY"),
        Provider.GEMINI: ("gemini_key", "GEMINI_API_KEY"),
        Provider.ELEVENLABS: ("elevenlabs_key", "XI_API_KEY"),
        Provider.SIXTYDB: ("sixtydb_key", "SIXTYDB_API_KEY"),
        Provider.STABLE_DIFFUSION: ("diffusion_key", "DIFFUSION_KEY"),
        Provider.MIDJOURNEY: ("midjourney_key", "MIDJOURNEY_KEY"),
        Provider.GOOGLE_SEARCH: ("google_search_key", "API_KEY"),
        Provider.GOOGLE_SEARCH_ENGINE_ID: (
            "google_search_engine_id",
            "SEARCH_ENGINE_ID",
        ),
        Provider.TWITCH_CLIENT: ("twitch_client_id", "TWITCH_CLIENT"),
        Provider.TWITCH_SECRET: ("twitch_client_secret", "TWITCH_CLIENT_SECRET"),
    }

    def get(self, provider: str) -> str | None:
        field, _ = self.FIELDS[provider]
        return getattr(self, field, "") or None

    @classmethod
    def key_for(cls, user, provider: str) -> str | None:
        field, setting = cls.FIELDS[provider]
        service_key = getattr(settings, setting, None) or None
        if user is None:
            return service_key

        if not getattr(user, "is_authenticated", False):
            return

        if user.use_service_api_keys:
            return service_key

        keys = cls.objects.filter(user=user).first()
        return (getattr(keys, field, "") or None) if keys else None

    @staticmethod
    def mask(value: str | None) -> str:
        if not value:
            return ""

        if len(value) < 12:
            return "•" * 8
        return f"{value[:3]}{'•' * 8}{value[-4:]}"

    @hook(AFTER_UPDATE, on_commit=True)
    def update_user_voices(self):
        from apps.videomanagement.tasks import update_user_voices

        for field, provider in VOICE_KEY_FIELDS.items():
            if self.has_changed(field) and getattr(self, field):
                update_user_voices.delay(self.user_id, provider)


class AbstractCustomProvider(models.Model):
    """Shared connection settings; each concrete provider keeps its own table."""

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    endpoint_url = models.URLField()
    extra_parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional JSON fields sent with generation requests",
    )
    auth_type = models.CharField(
        max_length=20,
        choices=AuthType.choices,
        default=AuthType.BEARER,
    )
    auth_header_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Required if auth_type is 'header' (e.g., 'x-api-key')",
    )
    api_key = EncryptedCharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Secret API key, token, or credentials",
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.name} ({self.user.username if self.user else ''})"

    def get_auth_headers(self):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        auth = None

        if self.auth_type == AuthType.BEARER and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        elif (
            self.auth_type == AuthType.HEADER and self.auth_header_name and self.api_key
        ):
            headers[self.auth_header_name] = self.api_key

        elif self.auth_type == AuthType.BASIC and self.api_key:
            username, password = (
                self.api_key.split(":", 1)
                if ":" in self.api_key
                else (self.api_key, "")
            )
            auth = HTTPBasicAuth(username, password)

        return headers, auth

    def request_payload(self, fields):
        """Required generation fields take precedence over optional parameters."""
        return {**self.extra_parameters, **fields}


class UserCustomTTSProvider(LifecycleModelMixin, AbstractCustomProvider):
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="custom_tts_providers",
    )
    name = models.CharField(
        max_length=50, help_text="Unique identifier, e.g., 'my_local_tts'"
    )
    endpoint_url = models.URLField(
        help_text="The POST endpoint URL for the TTS service"
    )
    voices_url = models.CharField(max_length=500, null=True, blank=True)
    text_field_name = models.CharField(max_length=50, default="text")
    voice_field_name = models.CharField(max_length=50, default="voice_id")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_user_custom_tts_provider",
            )
        ]

    @hook(AFTER_CREATE, on_commit=True)
    def create_voices(self):
        from apps.videomanagement.tasks import update_user_voices

        update_user_voices.delay(self.user.id, self.name)

    @hook(AFTER_DELETE, on_commit=True)
    def delete_voices(self):
        from apps.videomanagement.models import VoiceModel

        VoiceModel.objects.filter(created_by=self.user, provider=self.name).delete()


class VisualOutputType(models.TextChoices):
    IMAGE = "IMAGE", "Image"
    VIDEO = "VIDEO", "Video"


class UserCustomVisualProvider(AbstractCustomProvider):
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="custom_visual_providers",
    )
    output_type = models.CharField(max_length=10, choices=VisualOutputType.choices)
    endpoint_url = models.URLField(max_length=500)
    prompt_field_name = models.CharField(max_length=50, default="prompt")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_user_custom_visual_provider",
            )
        ]
        ordering = ["name", "id"]
