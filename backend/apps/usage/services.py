"""Normalize provider measurements without inventing missing token counts."""

import logging
from contextlib import contextmanager
from contextvars import ContextVar

from django.db import DatabaseError, transaction

from apps.usage.models import AIUsage
from apps.usage.tokens import normalize_token_usage
from apps.usage.pricing import measured_cost

logger = logging.getLogger(__name__)
current_video = ContextVar("usage_video", default=None)


@contextmanager
def video_usage(video):
    token = current_video.set(video)
    try:
        yield
    finally:
        current_video.reset(token)


def record_usage(
    user,
    service,
    provider,
    model="",
    usage=None,
    *,
    characters=0,
    images=0,
    seconds=0,
    custom=False,
):
    if not getattr(user, "is_authenticated", False):
        return
    tokens = normalize_token_usage(usage, provider=None if custom else provider)
    video = current_video.get()
    if video is not None and video.created_by_id != user.pk:
        video = None
    cost, cost_details = measured_cost(
        service,
        provider,
        model,
        {
            **tokens,
            "characters": characters,
            "images": images,
            "seconds": seconds if seconds or service not in ("video", "stt") else None,
            "requests": 1,
        },
        usage,
        custom=custom,
    )
    try:
        # A failed measurement must not discard successfully generated content.
        # The savepoint also keeps an enclosing request transaction usable.
        with transaction.atomic():
            AIUsage.objects.create(
                user=user,
                service=service,
                provider=provider,
                model=model,
                key_source="personal"
                if custom or not user.use_service_api_keys
                else "service",
                **tokens,
                characters=characters,
                images=images,
                seconds=seconds,
                video=video,
                cost_usd=cost,
                cost_details=cost_details,
            )
    except DatabaseError:
        logger.error("Could not save AI usage for %s/%s", provider, service)
