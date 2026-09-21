import logging
import os
import uuid

from django.conf import settings
from openai import OpenAI
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.apikeysmanagement.models import ApiKeys, Provider

from ..prompt_utils import format_sora_prompt

logger = logging.getLogger(__name__)

SORA_ALLOWED_SECONDS = (4, 8, 12)


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

    `reference` is a still that the clip should look like. Every sentence is its own
    job with no memory of the last one, so settings.SORA_STYLE and this frame are what
    keep a video from looking like a dozen unrelated stock shots.
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
            title=title, image_description=prompt, style=settings.SORA_STYLE
        ),
        seconds=str(seconds),
        size=settings.SORA_SIZE,
    )

    client = OpenAI(api_key=ApiKeys.key_for(user, Provider.OPENAI))
    if reference and os.path.isfile(reference):
        with open(reference, "rb") as anchor:
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
