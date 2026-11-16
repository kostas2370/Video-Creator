import logging

from django.db import DatabaseError, transaction

from .models import LLMTrace
from .services import current_video

logger = logging.getLogger(__name__)


def record_llm_trace(
    user, model, prompt, response, *, attempt, errors=(), has_reference_image=False
):
    video = current_video.get()
    if (
        video is None
        or not getattr(user, "is_authenticated", False)
        or video.created_by_id != user.pk
    ):
        return
    try:
        with transaction.atomic():
            LLMTrace.objects.create(
                video=video,
                model=model,
                prompt=prompt,
                response=response,
                attempt=attempt,
                validation_errors=list(errors),
                has_reference_image=has_reference_image,
            )
    except DatabaseError:
        logger.error("Could not save language model trace for video %s", video.pk)
