from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
from django_lifecycle import LifecycleModelMixin, hook, AFTER_UPDATE


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
        from .tasks import import_user_voices

        for field, provider in VOICE_KEY_FIELDS.items():
            if self.has_changed(field) and getattr(self, field):
                import_user_voices.delay(self.user_id, provider)
