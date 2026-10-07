from .registry import DEFAULT_PROVIDERS, ImageProviderRegistry
# Import adapters to register their module-level handlers.
from . import bing, custom, diffusion, google_images, midjourney, openai_images, sora  # noqa: F401

VIDEO_PROVIDERS = ImageProviderRegistry.video_providers


__all__ = ["DEFAULT_PROVIDERS", "ImageProviderRegistry", "VIDEO_PROVIDERS"]
