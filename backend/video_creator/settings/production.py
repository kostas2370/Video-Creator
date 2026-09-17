"""Production settings.

`video_creator.settings` resolves to this module when ENV=prod.
"""

import os

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, SIMPLE_JWT

DEBUG = False

# Comma-separated in .env, e.g. ALLOWED_HOSTS=viddie.example.com,www.viddie.example.com.
# Falls back to "*" so an existing deployment that never set it keeps answering; narrow
# it as soon as the hostnames are known.
ALLOWED_HOSTS = [
    host.strip()
    for host in (os.getenv("ALLOWED_HOSTS") or "*").split(",")
    if host.strip()
]

# Served over https, so the auth cookies are marked Secure and the SameSite=None that
# a cross-site frontend needs becomes legal — browsers reject that pairing without
# Secure. The two move together; see the matching note in local.py for why development
# does the opposite.
COOKIES_SECURE = True
CROSS_SITE_SAMESITE = "None"

# Re-derived from the values above. base.py computed these from its development
# defaults, so overriding COOKIES_SECURE alone would leave them behind.
SIMPLE_JWT = {**SIMPLE_JWT, "AUTH_COOKIE_SECURE": COOKIES_SECURE}
CSRF_COOKIE_SECURE = COOKIES_SECURE
CSRF_COOKIE_SAMESITE = CROSS_SITE_SAMESITE
SESSION_COOKIE_SECURE = COOKIES_SECURE
SESSION_COOKIE_SAMESITE = CROSS_SITE_SAMESITE

# Database
# Port 3307 rather than 3306 — that is what the db service publishes in
# docker-compose.yml.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE", "db"),
        "USER": os.getenv("MYSQL_USER"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD"),
        "HOST": os.getenv("MYSQL_HOST"),
        "PORT": "3307",
    }
}

# Email — real messages, via the SMTP credentials base.py reads from .env.
# `or` rather than a getenv default: .env_example ships the key blank, and "" would
# otherwise win and leave Django with no mail backend at all.
EMAIL_BACKEND = (
    os.getenv("EMAIL_BACKEND") or "django.core.mail.backends.smtp.EmailBackend"
)

# Static files
# With DEBUG off, urls.py stops serving these and Django hands them to whatever is in
# front of it, so `manage.py collectstatic` needs somewhere to put them. Media is
# already served by the nginx frontend container straight off the shared volume.
STATIC_ROOT = BASE_DIR / "staticfiles"
