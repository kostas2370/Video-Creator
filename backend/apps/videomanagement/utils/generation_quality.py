from django.conf import settings


def image_quality_for(generation_mode="STANDARD"):
    if generation_mode == "ECONOMY":
        return "low" if settings.IMAGE_QUALITY == "low" else "medium"
    return settings.IMAGE_QUALITY
