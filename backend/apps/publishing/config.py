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


def setup_message(platform):
    config = configuration(platform)
    if not config.get("client_id") or not config.get("client_secret"):
        return "The app owner needs to register this platform's developer app before accounts can connect."
    parsed = urlparse(settings.SOCIAL_PUBLIC_BASE_URL)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/") or parsed.username or parsed.password or parsed.query or parsed.fragment:
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
