"""Refresh and store account tokens under a database lock."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .connections import get_connection
from .http import ProviderError
from .models import Platform, SocialAccount


def needs_reconnect(account):
    return bool(
        account.expires_at
        and account.expires_at <= timezone.now() + timedelta(minutes=2)
        and (not account.refresh_token or account.platform == Platform.INSTAGRAM)
    )


@transaction.atomic
def access_token(account):
    account = SocialAccount.objects.select_for_update().get(pk=account.pk)
    if account.expires_at and account.expires_at <= timezone.now() + timedelta(minutes=2):
        if needs_reconnect(account):
            raise ProviderError("This account connection has expired. Reconnect it before publishing.")
        tokens = get_connection(account.platform).refresh_token(account.refresh_token)
        account.access_token = tokens["access_token"]
        account.refresh_token = tokens.get("refresh_token") or account.refresh_token
        account.expires_at = timezone.now() + timedelta(seconds=int(tokens.get("expires_in", 3600)))
        account.save(update_fields=["access_token", "refresh_token", "expires_at"])
    return account.access_token
