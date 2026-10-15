"""Normalize provider measurements without inventing missing token counts."""

import logging

from django.db import DatabaseError, transaction

from ..models import AIUsage

logger = logging.getLogger(__name__)


def value(obj, name):
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def count(obj, name):
    number = value(obj, name)
    return number if type(number) is int and number >= 0 else None


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
    input_tokens = count(usage, "input_tokens")
    if input_tokens is None:
        input_tokens = count(usage, "prompt_tokens")
    output_tokens = count(usage, "output_tokens")
    if output_tokens is None:
        output_tokens = count(usage, "completion_tokens")
    if provider == "GEMINI":
        input_tokens = count(usage, "prompt_token_count")
        output_tokens = count(usage, "candidates_token_count")
    if provider == "ANTHROPIC" and input_tokens is not None:
        input_tokens += count(usage, "cache_read_input_tokens") or 0
        input_tokens += count(usage, "cache_creation_input_tokens") or 0
    total_tokens = count(usage, "total_tokens")
    if provider == "GEMINI":
        total_tokens = count(usage, "total_token_count")
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
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
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                characters=characters,
                images=images,
                seconds=seconds,
            )
    except DatabaseError:
        logger.error("Could not save AI usage for %s/%s", provider, service)
