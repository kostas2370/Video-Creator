import base64
import logging
import os
import uuid

from django.conf import settings
from openai import OpenAI
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.apikeysmanagement.models import ApiKeys, Provider

from ..prompt_utils import format_image_prompt

from .registry import ImageProviderRegistry

logger = logging.getLogger(__name__)


@ImageProviderRegistry.register("OPENAI")
def generate_openai_image(
    prompt: str,
    dir_name: str,
    style: str,
    title: str = "",
    user=None,
    reference: str = None,
    *args,
    **kwargs,
) -> str:
    """Generate or edit an image using the configured GPT image model."""
    logger.warning("API CALL IN OPENAI IMAGES")

    client = OpenAI(api_key=ApiKeys.key_for(user, Provider.OPENAI))

    image_prompt = format_image_prompt(title=title, image_description=prompt)
    # Express the visual style in the prompt.
    if style:
        image_prompt = f"{image_prompt}\nStyle: {style}"

    request = dict(
        model=settings.IMAGE_MODEL,
        prompt=image_prompt,
        size=settings.IMAGE_SIZE,
        quality=settings.IMAGE_QUALITY,
        n=1,
        output_format="png",
    )
    if reference and os.path.isfile(reference):
        request["prompt"] += (
            "\nUse the reference as the visual identity guide for this video. "
            "Preserve recurring characters' facial features, hair, clothing, and "
            "proportions, recurring objects, art style, and color palette. "
            "Create the new shot described above; change pose, framing, action, "
            "and location as required by the shot. Do not copy the old composition "
            "or introduce reference subjects that are absent from this shot."
        )
        if settings.IMAGE_MODEL in {"gpt-image-1", "gpt-image-1.5"}:
            request["input_fidelity"] = "high"
        with open(reference, "rb") as anchor:
            response = client.images.edit(image=anchor, **request)
    else:
        response = client.images.generate(**request)

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
