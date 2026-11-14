import os
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, FRONTEND_URL, SECRET_KEY, SIMPLE_JWT

DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in (os.getenv("ALLOWED_HOSTS") or "").split(",")
    if host.strip()
]

if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must name the hosts this deployment answers on. "
        "Set it to a comma separated list, for example "
        "ALLOWED_HOSTS=viddie.example.com,www.viddie.example.com"
    )


if (
    len(SECRET_KEY) < 50
    or len(set(SECRET_KEY)) < 5
    or SECRET_KEY.startswith("django-insecure-")
):
    raise ImproperlyConfigured(
        "Production SECRET_KEY must be a strong random secret of at least 50 characters."
    )

SECURE_SSL_REDIRECT = True
# Only the private nginx upstream may reach Django; it overwrites this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Shared across API workers; keep rate-limit counters separate from Celery data.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("CACHE_URL") or "redis://redis-stack-server:6379/2",
    }
}

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
        "PORT": os.getenv("MYSQL_PORT") or "3306",
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

frontend_origin = urlparse(FRONTEND_URL)
if (
    frontend_origin.scheme != "https"
    or not frontend_origin.netloc
    or frontend_origin.path
):
    raise ImproperlyConfigured("Production FRONTEND_URL must be an HTTPS origin.")

CORS_ALLOW_ALL_ORIGINS = False
CORS_ORIGIN_ALLOW_ALL = False
CORS_ALLOWED_ORIGINS = [FRONTEND_URL]
CSRF_TRUSTED_ORIGINS = [FRONTEND_URL]

STATIC_ROOT = BASE_DIR / "staticfiles"
