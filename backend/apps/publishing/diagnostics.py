"""Log operation context without exception messages, URLs or credentials."""

import logging

logger = logging.getLogger("apps.publishing")


def log_failure(operation, *, platform, reference, error):
    logger.warning(
        "Publishing %s failed: platform=%s reference=%s error_type=%s",
        operation, platform, reference, type(error).__name__,
    )
