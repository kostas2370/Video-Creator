import os
import sys

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = (
    os.getenv("EMAIL_BACKEND") or "django.core.mail.backends.console.EmailBackend"
)

if "test" in sys.argv:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "null": {
                "class": "logging.NullHandler",
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["null"],
                "level": "CRITICAL",
                "propagate": False,
            },
        },
    }

else:
    LOGGING = {  # noqa: F405
        **LOGGING,  # noqa: F405
        "root": {**LOGGING["root"], "level": os.getenv("LOG_LEVEL") or "INFO"},  # noqa: F405
    }
