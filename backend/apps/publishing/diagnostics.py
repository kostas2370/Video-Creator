"""Log operation context without exception messages, URLs or credentials."""

import logging

from .http import ProviderError

logger = logging.getLogger("apps.publishing")


def log_failure(operation, *, platform, reference, error):
    provider = error if isinstance(error, ProviderError) else None
    logger.warning(
        "Publishing %s failed: platform=%s reference=%s error_type=%s stage=%s provider_code=%s http_status=%s",
        operation, platform, reference, type(error).__name__,
        provider.stage if provider else None,
        provider.provider_code if provider else None,
        provider.http_status if provider else None,
    )
