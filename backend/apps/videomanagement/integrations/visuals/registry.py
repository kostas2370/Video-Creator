from functools import partial

from apps.apikeysmanagement.models import UserCustomVisualProvider, VisualOutputType
from apps.videomanagement.integrations.registry import ProviderNames, ProviderRegistry

DEFAULT_PROVIDERS = {"WEB": "bing", "AI": "OPENAI"}


class ImageProviderRegistry(ProviderRegistry):
    mode_label = "visual"
    default_mode = "AI"
    defaults = DEFAULT_PROVIDERS
    video_providers = ProviderNames(mode="AI", output_type="VIDEO")

    @classmethod
    def register(cls, name, mode="AI", output_type="IMAGE", supports_reference=False):
        if output_type not in ("IMAGE", "VIDEO"):
            raise ValueError(f"Unsupported visual output type: {output_type}")
        return super().register(
            name,
            mode=mode,
            output_type=output_type,
            supports_reference=supports_reference,
        )

    @classmethod
    def is_video(cls, name, user=None, mode="AI"):
        """Prefer built-in metadata; scope custom lookups to the requesting owner."""
        if mode != "AI":
            return False
        entry = cls.registration(name, mode)
        if entry is not None:
            return entry.capabilities["output_type"] == "VIDEO"
        if not name or not getattr(user, "is_authenticated", False):
            return False
        return UserCustomVisualProvider.objects.filter(
            user=user,
            name=name,
            output_type=VisualOutputType.VIDEO,
        ).exists()

    @classmethod
    def supports_reference(cls, name=None, mode="AI"):
        entry = cls.registration(name, mode)
        return bool(entry and entry.capabilities.get("supports_reference"))

    @classmethod
    def resolve(cls, mode, provider=None):
        handler = cls.get(provider, mode)
        if handler is None:
            raise ValueError(f"No visual provider configured for mode: {mode}")
        if cls.registration(provider, mode) is None and mode in cls._fallback_providers:
            return partial(handler, provider_name=provider or cls.defaults[mode])
        return handler
