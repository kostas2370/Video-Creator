import logging

from celery import shared_task
from django.contrib.auth import get_user_model

from apps.videomanagement.utils import gpt_utils

from .models import Provider

logger = logging.getLogger(__name__)

VOICE_IMPORTS = {
    Provider.ELEVENLABS: ("eleven_labs", "get_voices_from_labs"),
    Provider.SIXTYDB: ("60db", "get_voices_from_60db"),
}


@shared_task
def import_user_voices(user_id: int, provider: str):
    # Local import prevents circular import when models.py imports tasks.py
    from apps.videomanagement.models import VoiceModel

    provider_name, fetcher = VOICE_IMPORTS[provider]
    user = get_user_model().objects.filter(pk=user_id).first()
    if user is None:
        return 0

    try:
        voices = getattr(gpt_utils, fetcher)(user)
    except Exception:
        logger.exception("Could not read %s voices for user %s", provider, user_id)
        raise

    existing = set(
        VoiceModel.objects.filter(created_by=user, provider=provider_name).values_list(
            "path", flat=True
        )
    )

    added = [
        VoiceModel(
            name=voice["name"],
            provider=provider_name,
            type="API",
            path=voice["voice_id"],
            sample=voice.get("preview_url", ""),
            created_by=user,
        )
        for voice in voices
        if voice["voice_id"] not in existing
    ]

    VoiceModel.objects.bulk_create(added)
    logger.info("Imported %s %s voices for user %s", len(added), provider, user_id)

    return len(added)
