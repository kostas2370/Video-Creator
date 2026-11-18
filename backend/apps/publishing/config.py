"""Deployment configuration; no OAuth secrets are returned to the browser."""

import re
from urllib.parse import urlparse

from django.conf import settings
from rest_framework.exceptions import ValidationError

from .models import Platform


def configuration(platform):
    if platform not in Platform.values:
        raise ValidationError("Choose YouTube, TikTok, or Instagram.")
    return settings.SOCIAL_PUBLISHING.get(platform, {})


def local_youtube_origin(platform):
    """Allow HTTP only on literal localhost in the local YouTube workflow."""
    try:
        parsed = urlparse(settings.SOCIAL_PUBLIC_BASE_URL)
        parsed.port  # Reject malformed or out-of-range ports.
        return (
            platform == Platform.YOUTUBE and settings.DEBUG
            and getattr(settings, "ENV", "prod") != "prod"
            and parsed.scheme == "http" and parsed.hostname == "localhost"
            and not parsed.username and not parsed.password
            and parsed.path in ("", "/") and not parsed.query and not parsed.fragment
        )
    except ValueError:
        return False


def setup_message(platform):
    config = configuration(platform)
    if not config.get("client_id") or not config.get("client_secret"):
        return "The app owner needs to register this platform's developer app before accounts can connect."
    try:
        parsed = urlparse(settings.SOCIAL_PUBLIC_BASE_URL)
        parsed.port
    except ValueError:
        return "The app owner needs to configure a valid callback origin."
    local = local_youtube_origin(platform)
    if local and settings.FRONTEND_URL.rstrip("/") != settings.SOCIAL_PUBLIC_BASE_URL.rstrip("/"):
        return "Use the same localhost origin for the frontend and YouTube callback address."
    if (parsed.scheme != "https" and not local) or not parsed.netloc or parsed.path not in ("", "/") or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return "The app owner needs to configure its public HTTPS address for account connections."
    if platform == Platform.INSTAGRAM and not re.fullmatch(r"v\d+\.\d+", config.get("api_version", "")):
        return "The app owner needs to configure the Meta Graph API version selected for the developer app."
    return ""


def require_configured(platform):
    message = setup_message(platform)
    if message:
        raise ValidationError(message)
    return configuration(platform)


def callback_url(platform):
    return f"{settings.SOCIAL_PUBLIC_BASE_URL.rstrip('/')}/api/publishing/oauth/{platform}/callback/"
