import base64
import logging
import os

from django.core.files.base import ContentFile
from apps.videomanagement.models import MediaAsset

from django.conf import settings
from openai import OpenAI
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.apikeysmanagement.models import ApiKeys, Provider
from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from apps.usage.services import record_usage
from apps.videomanagement.utils.prompt_utils import format_image_prompt

logger = logging.getLogger(__name__)

# GPT Image 2 accepts custom dimensions in multiples of 16.
# Older GPT Image models use their supported portrait/landscape presets.
FRAME_IMAGE_SIZES = {
    "LANDSCAPE": "1536x864",
    "PORTRAIT": "864x1536",
    "SQUARE": "1024x1024",
}
LEGACY_FRAME_IMAGE_SIZES = {
    "LANDSCAPE": "1536x1024",
    "PORTRAIT": "1024x1536",
    "SQUARE": "1024x1024",
}


def image_size_for_frame(video_format):
    sizes = (
        FRAME_IMAGE_SIZES
        if settings.IMAGE_MODEL.startswith("gpt-image-2")
        else LEGACY_FRAME_IMAGE_SIZES
    )
    # Standalone requests (such as covers) retain their configured size.
    return sizes.get(video_format, settings.IMAGE_SIZE)


@ImageProviderRegistry.register("OPENAI", supports_reference=True)
def generate_openai_image(
    prompt: str,
    dir_name: str,
    style: str,
    title: str = "",
    user=None,
    reference: str = None,
    reference_role: str = "both",
    *args,
    video_format: str = None,
    **kwargs,
) -> str:
    """Generate or edit an image using the configured GPT image model."""
    logger.warning("API CALL IN OPENAI IMAGES")

    client = OpenAI(api_key=ApiKeys.key_for(user, Provider.OPENAI))

    has_reference = bool(reference and os.path.isfile(reference))
    image_prompt = format_image_prompt(
        title=title,
        image_description=prompt,
        style=style,
        preserve_reference=has_reference,
        reference_role=reference_role,
    )

    request = dict(
        model=settings.IMAGE_MODEL,
        prompt=image_prompt,
        size=image_size_for_frame(video_format),
        quality=settings.IMAGE_QUALITY,
        n=1,
        output_format="png",
    )
    if has_reference:
        if settings.IMAGE_MODEL in {"gpt-image-1", "gpt-image-1.5"}:
            request["input_fidelity"] = "high"
        with open(reference, "rb") as anchor:
            response = client.images.edit(image=anchor, **request)
    else:
        response = client.images.generate(**request)

    record_usage(
        user,
        "images",
        Provider.OPENAI,
        settings.IMAGE_MODEL,
        getattr(response, "usage", None),
        images=len(response.data or []),
    )

    # gpt-image always answers with base64 and never populates `url`.
    if not response.data or not response.data[0].b64_json:
        logger.error("Image model %s returned no image data", settings.IMAGE_MODEL)
        raise APIException(
            detail="The image model returned no image",
            code=status.HTTP_400_BAD_REQUEST,
        )

    asset = MediaAsset.from_visual(
        user=user,
        upload=ContentFile(base64.b64decode(response.data[0].b64_json), name="generated.png"),
        title=(title or "AI generated image")[:100],
        tags=["ai image"], kind=MediaAsset.Kind.IMAGE,
    )
    return asset.file.path
