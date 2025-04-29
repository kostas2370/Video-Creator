modes = {
    "AI": {
        "DALL-E": "generate_from_dalle",
        "stable-diffusion": "generate_from_diffusion",
        "midjourney": "generate_from_midjourney",
    },
    "WEB": {"bing": "download_image", "google": "download_image_from_google"},
}


default_providers = {"WEB": "bing", "AI": "DALL-E"}


api_providers = {"open_ai": "tts_from_open_api", "eleven_labs": "tts_from_eleven_labs"}
