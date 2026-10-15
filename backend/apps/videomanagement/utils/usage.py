"""Normalize provider measurements without inventing missing token counts."""

import logging

from django.db import DatabaseError, transaction

from ..models import AIUsage
from .token_usage import normalize_token_usage

logger = logging.getLogger(__name__)


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
            )
    except DatabaseError:
        logger.error("Could not save AI usage for %s/%s", provider, service)
