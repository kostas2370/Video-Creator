# Import adapters to register their module-level handlers.
from apps.videomanagement.integrations.visuals.registry import (
    DEFAULT_PROVIDERS,
    ImageProviderRegistry,
)

from . import (  # noqa: F401
    bing,
    custom,
    diffusion,
    google_images,
    midjourney,
    openai_images,
    sora,
    kling,
    runway,
    gemini_video,
)

VIDEO_PROVIDERS = ImageProviderRegistry.video_providers


__all__ = ["DEFAULT_PROVIDERS", "ImageProviderRegistry", "VIDEO_PROVIDERS"]
