modes = \
    {"AI":
        {"dall-e": "generate_from_dalle",
         "stable-diffusion": "generate_from_diffusion",
         "midjourney": "generate_from_midjourney"},
     "WEB": {
          "bing": "download_image",
          "google": "download_image_from_google"}
     }


default_providers = {
    "WEB": "bing",
    "AI": "dall-e"
}

model_calls = {
    "gpt": "gpt_call",
    "claude": "claude_call",
    "gemini": "gemini_call"
}