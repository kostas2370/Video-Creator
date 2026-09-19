import os

from .base import *  # noqa: F401,F403
from .base import BASE_DIR

DEBUG = True
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

EMAIL_BACKEND = (
    os.getenv("EMAIL_BACKEND") or "django.core.mail.backends.console.EmailBackend"
)

if 'test' in sys.argv:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'null': {
                'class': 'logging.NullHandler',
            },
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['null'],
                'level': 'CRITICAL',
                'propagate': False,
            },
        },
    }

else:
    LOGGING = {  # noqa: F405
    **LOGGING,  # noqa: F405
    "root": {**LOGGING["root"], "level": os.getenv("LOG_LEVEL") or "INFO"},  # noqa: F405
}