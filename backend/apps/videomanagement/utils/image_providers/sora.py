import logging
import os
import uuid
from io import BytesIO

from django.conf import settings
from openai import OpenAI
from PIL import Image, ImageOps
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.apikeysmanagement.models import ApiKeys, Provider

from ..prompt_utils import format_sora_prompt

from .registry import ImageProviderRegistry

logger = logging.getLogger(__name__)

SORA_ALLOWED_SECONDS = (4, 8, 12)


@ImageProviderRegistry.register("sora", output_type="VIDEO")
def generate_from_sora(
    prompt: str,
    dir_name: str,
    style: str = "",
    title: str = "",
    duration: float = 0,
    reference: str = None,
    user=None,
    *args,
    **kwargs,
) -> str:
    """
    Generate a short video clip for one sentence with Sora.

    Returns the path to an .mp4 rather than an image. process_scene already branches on
    file type, so the rest of the pipeline treats it like any other scene visual: the
    narration stays the source of truth for timing and handle_video fits the clip to it.

    `duration` is the narration length for this sentence. Sora only renders 4, 8 or 12
    second clips, so the shortest one that covers the narration is requested; anything
    longer than 12s is covered by handle_video holding the final frame.

    `reference` is the preceding clip's closing frame. Every sentence is its own
    job, so this opening frame carries visual continuity into the next shot.
    """
    logger.warning("API CALL IN SORA")

    # No narration to fit means no duration is passed; fall back to the configured
    # silent scene length instead of collapsing to the 4s minimum by accident.
    wanted = duration or settings.SILENT_SCENE_SECONDS
    seconds = next(
        (s for s in SORA_ALLOWED_SECONDS if s >= wanted), SORA_ALLOWED_SECONDS[-1]
    )
    request = dict(
        model=settings.SORA_MODEL,
        prompt=format_sora_prompt(
            title=title, image_description=prompt, style=style or settings.SORA_STYLE
        ),
        seconds=str(seconds),
        size=settings.SORA_SIZE,
    )

    client = OpenAI(api_key=ApiKeys.key_for(user, Provider.OPENAI))
    if reference and os.path.isfile(reference):
        request["prompt"] += (
            " Continue from the supplied opening frame into the action described "
            "above. Preserve recurring subjects' identity, wardrobe, proportions, "
            "and the established visual style. Keep motion, lighting, and spatial "
            "relationships coherent unless the shot explicitly calls for a change."
        )
        # Sora requires the reference to match the requested video dimensions.
        size = tuple(int(value) for value in settings.SORA_SIZE.split("x"))
        with Image.open(reference) as source, BytesIO() as anchor:
            ImageOps.fit(ImageOps.exif_transpose(source).convert("RGB"), size).save(
                anchor, format="PNG"
            )
            anchor.name = "reference.png"
            anchor.seek(0)
            video = client.videos.create_and_poll(input_reference=anchor, **request)
    else:
        video = client.videos.create_and_poll(**request)

    if video.status != "completed":
        reason = getattr(video, "error", None)
        code = getattr(reason, "code", None) or "unknown"
        message = getattr(reason, "message", None) or "no reason given"
        logger.error(
            "Sora job %s ended as %s: %s - %s", video.id, video.status, code, message
        )
        raise APIException(
            detail=f"Sora did not return a video ({video.status}: {code} - {message})",
            code=status.HTTP_400_BAD_REQUEST,
        )

    filename = f"{dir_name}{uuid.uuid4()}.mp4"
    client.videos.download_content(video.id, variant="video").write_to_file(filename)

    return filename
