import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, FRONTEND_URL, SIMPLE_JWT

DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in (os.getenv("ALLOWED_HOSTS") or "").split(",")
    if host.strip()
]

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must name the hosts this deployment answers on. "
        "Set it to a comma separated list, for example "
        "ALLOWED_HOSTS=viddie.example.com,www.viddie.example.com"
    )


COOKIES_SECURE = True
CROSS_SITE_SAMESITE = "None"

TRUSTED_PROXY_HOPS = int(os.getenv("TRUSTED_PROXY_HOPS") or 1)


SIMPLE_JWT = {**SIMPLE_JWT, "AUTH_COOKIE_SECURE": COOKIES_SECURE}
CSRF_COOKIE_SECURE = COOKIES_SECURE
CSRF_COOKIE_SAMESITE = CROSS_SITE_SAMESITE
SESSION_COOKIE_SECURE = COOKIES_SECURE
SESSION_COOKIE_SAMESITE = CROSS_SITE_SAMESITE


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE", "db"),
        "USER": os.getenv("MYSQL_USER"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD"),
        "HOST": os.getenv("MYSQL_HOST"),
        "PORT": os.getenv("MYSQL_PORT", "3307"),
    }
}

EMAIL_BACKEND = (
    os.getenv("EMAIL_BACKEND") or "django.core.mail.backends.smtp.EmailBackend"
)

# base.py defaults this to the local dev server, which would email dead reset links in
# prod. With FRONTEND_URL unset, guess https:// the first concrete ALLOWED_HOSTS entry —
# a wildcard-only list leaves the base default, and is worth setting explicitly.
FRONTEND_URL = (os.getenv("FRONTEND_URL") or "").rstrip("/") or next(
    (f"https://{host}" for host in ALLOWED_HOSTS if "*" not in host), FRONTEND_URL
)

CORS_ALLOW_ALL_ORIGINS = False
CORS_ORIGIN_ALLOW_ALL = False
CORS_ALLOWED_ORIGINS = [FRONTEND_URL]
CSRF_TRUSTED_ORIGINS = [FRONTEND_URL]

STATIC_ROOT = BASE_DIR / "staticfiles"
