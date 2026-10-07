import sys
from functools import partial

DEFAULT_PROVIDERS = {"WEB": "bing", "AI": "OPENAI"}


class ImageProviderRegistry:
    """Resolve module-level visual handlers at call time, like TTSRegistry."""

    _providers = {}
    _fallback_providers = {}
    video_providers = set()

    @classmethod
    def is_video(cls, name, user=None):
        """Resolve output metadata without sharing custom names across users."""
        if name in cls._providers.get("AI", {}):
            return name in cls.video_providers
        if not name or not getattr(user, "is_authenticated", False):
            return False
        from apps.apikeysmanagement.models import (
            UserCustomVisualProvider,
            VisualOutputType,
        )

        return UserCustomVisualProvider.objects.filter(
            user=user, name=name, output_type=VisualOutputType.VIDEO
        ).exists()

    @classmethod
    def register(cls, name: str, mode: str = "AI", output_type: str = "IMAGE"):
        if mode not in DEFAULT_PROVIDERS:
            raise ValueError(f"Unsupported visual mode: {mode}")
        if output_type not in ("IMAGE", "VIDEO"):
            raise ValueError(f"Unsupported visual output type: {output_type}")

        def decorator(func):
            cls._providers.setdefault(mode, {})[name] = (func.__module__, func.__name__)
            if output_type == "VIDEO":
                cls.video_providers.add(name)
            else:
                cls.video_providers.discard(name)
            return func

        return decorator

    @classmethod
    def register_fallback(cls, mode: str = "AI"):
        if mode not in DEFAULT_PROVIDERS:
            raise ValueError(f"Unsupported visual mode: {mode}")

        def decorator(func):
            cls._fallback_providers[mode] = (func.__module__, func.__name__)
            return func

        return decorator

    @classmethod
    def get(cls, name: str = None, mode: str = "AI"):
        if mode not in DEFAULT_PROVIDERS:
            raise ValueError(f"Unsupported visual mode: {mode}")
        providers = cls._providers.get(mode, {})
        name = name or DEFAULT_PROVIDERS[mode]
        entry = (
            providers.get(name)
            or cls._fallback_providers.get(mode)
            or providers[DEFAULT_PROVIDERS[mode]]
        )
        module_name, function_name = entry
        return getattr(sys.modules[module_name], function_name)

    @classmethod
    def resolve(cls, mode: str, provider: str = None):
        handler = cls.get(provider, mode=mode)
        name = provider or DEFAULT_PROVIDERS[mode]
        if name not in cls._providers.get(mode, {}) and mode in cls._fallback_providers:
            return partial(handler, provider_name=name)
        return handler
