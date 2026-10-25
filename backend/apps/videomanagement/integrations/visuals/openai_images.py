import base64
import logging
import os
import uuid

from django.conf import settings
from openai import OpenAI
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.apikeysmanagement.models import ApiKeys, Provider
from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from apps.videomanagement.services.usage import record_usage
from apps.videomanagement.utils.prompt_utils import format_image_prompt

logger = logging.getLogger(__name__)


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
        size=settings.IMAGE_SIZE,
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

    x = str(uuid.uuid4())
    with open(rf"{dir_name}{x}.png", "wb") as image_file:
        image_file.write(base64.b64decode(response.data[0].b64_json))

    return rf"{dir_name}{x}.png"
