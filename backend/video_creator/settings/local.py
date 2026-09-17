"""Development settings — a laptop, a docker-compose stack, and CI.

This is what `video_creator.settings` resolves to whenever ENV is anything but "prod".
"""

import os

from .base import *  # noqa: F401,F403
from .base import BASE_DIR

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Cookies are left non-Secure here on purpose. A Secure cookie is only stored over
# https; Chrome and Firefox make an exception for http://localhost, Safari does not, so
# marking the auth cookies Secure in development means Safari silently drops them and
# every reload logs the user back out.
#
# SameSite=None is itself invalid without Secure — browsers reject that pairing — so
# the two have to move together. base.py already sets COOKIES_SECURE = False and
# CROSS_SITE_SAMESITE = "Lax", which is what development wants; production.py flips
# both. See the matching block there.

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Email
# Nothing leaves the machine: every message is printed to the terminal running the
# server, so password resets and activation links can be read straight off stdout.
# Set EMAIL_BACKEND in .env to talk to a real SMTP server when that is what you
# actually want to test.
#
# `or` rather than a getenv default, as elsewhere: .env_example ships the key blank and
# "" would otherwise win and leave Django with no mail backend at all.
EMAIL_BACKEND = (
    os.getenv("EMAIL_BACKEND") or "django.core.mail.backends.console.EmailBackend"
)

# Logging
# Louder than production: INFO covers the generation and render tasks, which are the
# thing you are usually watching locally.
#
# Rebuilt rather than mutated in place: base.LOGGING is a module-level dict shared with
# production.py, and editing it here would reach that module too.
LOGGING = {  # noqa: F405
    **LOGGING,  # noqa: F405
    "root": {**LOGGING["root"], "level": os.getenv("LOG_LEVEL") or "INFO"},  # noqa: F405
}
