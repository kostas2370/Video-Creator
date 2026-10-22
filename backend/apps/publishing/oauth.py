"""One-use OAuth state bound to the signed-in creator and initiating browser."""

import hashlib
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import OAuthAttempt, SocialAccount
from .connections import get_connection
from .http import ProviderError

COOKIE_NAME = "publishing_oauth"
COOKIE_PATH = "/api/publishing/oauth/"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def begin(user, platform, video):
    state, browser = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    url = get_connection(platform).authorization_url(state)
    OAuthAttempt.objects.filter(expires_at__lt=timezone.now()).delete()
    OAuthAttempt.objects.create(user=user, platform=platform, state_hash=digest(state),
                                browser_hash=digest(browser), expires_at=timezone.now() + timedelta(minutes=10), video=video)
    return url, browser


def consume(platform, state, browser):
    if not state or not browser:
        raise ValidationError("This connection request is missing or expired. Start again from the app.")
    with transaction.atomic():
        attempt = OAuthAttempt.objects.select_for_update().select_related("user").filter(
            platform=platform, state_hash=digest(state), used=False, expires_at__gt=timezone.now()
        ).first()
        if not attempt or not attempt.user.is_active or not secrets.compare_digest(attempt.browser_hash, digest(browser)):
            raise ValidationError("This connection request is missing or expired. Start again from the app.")
        attempt.used = True
        attempt.save(update_fields=["used"])
    return attempt


def finish(attempt, code):
    connection = get_connection(attempt.platform)
    stage = "token_exchange"
    try:
        tokens = connection.exchange_code(code)
        stage = "account_lookup"
        profiles = connection.identities(tokens)
    except ProviderError as exc:
        exc.stage = stage
        raise
    if not profiles:
        raise ValidationError("No eligible account was found. Instagram needs a professional account linked to a Facebook Page.")
    expiry = timezone.now() + timedelta(seconds=int(tokens.get("expires_in", 3600)))
    with transaction.atomic():
        for profile in profiles:
            existing = SocialAccount.objects.filter(user=attempt.user, platform=attempt.platform, external_id=profile["external_id"]).first()
            SocialAccount.objects.update_or_create(
                user=attempt.user, platform=attempt.platform, external_id=profile["external_id"],
                defaults={"display_name": profile["display_name"], "access_token": profile["access_token"],
                          "expires_at": expiry, "refresh_token": tokens.get("refresh_token") or (existing.refresh_token if existing else "")},
            )
