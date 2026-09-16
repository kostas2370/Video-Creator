modes = {
    "AI": {
        "DALL-E": "generate_from_dalle",
        # Returns a short clip per sentence instead of a still. Billed per second.
        "sora": "generate_from_sora",
        "stable-diffusion": "generate_from_diffusion",
        "midjourney": "generate_from_midjourney",
    },
    "WEB": {"bing": "download_image", "google": "download_image_from_google"},
}


default_providers = {"WEB": "bing", "AI": "DALL-E"}

# Providers that return footage rather than a still. The script is written differently
# for these — see defaults.video_format.
video_providers = {"sora"}


api_providers = {
    "open_ai": "tts_from_open_api",
    "eleven_labs": "tts_from_eleven_labs",
    "60db": "tts_from_60db",
}
