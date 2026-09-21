from . import bing, diffusion, google_images, midjourney, openai_images, sora

PROVIDERS = {
    "AI": {
        "DALL-E": (openai_images, "generate_from_dalle"),
        "sora": (sora, "generate_from_sora"),
        "stable-diffusion": (diffusion, "generate_from_diffusion"),
        "midjourney": (midjourney, "generate_from_midjourney"),
    },
    "WEB": {
        "bing": (bing, "download_image"),
        "google": (google_images, "download_image_from_google"),
    },
}

DEFAULT_PROVIDERS = {"WEB": "bing", "AI": "DALL-E"}

VIDEO_PROVIDERS = {"sora"}


def resolve(mode: str, provider: str = None):
    entry = PROVIDERS.get(mode, {}).get(provider or DEFAULT_PROVIDERS.get(mode))
    if entry is None:
        return None

    module, name = entry
    return getattr(module, name)
