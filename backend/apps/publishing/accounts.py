"""Refresh and store account tokens under a database lock."""

from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.common.credential_encryption import VAULT_PREFIX

from .connections import get_connection
from .http import ProviderError
from .models import Platform, SocialAccount


def needs_reconnect(account):
    has_access_token = getattr(account, "has_vault_access_token", None)
    if has_access_token is None:
        has_access_token = bool(account.access_token)
    if not has_access_token:
        return True
    if not account.expires_at or account.expires_at > timezone.now() + timedelta(
        minutes=2
    ):
        return False
    has_refresh_token = getattr(account, "has_vault_refresh_token", None)
    if has_refresh_token is None:
        has_refresh_token = bool(account.refresh_token)
    return not has_refresh_token or account.platform == Platform.INSTAGRAM


def accounts_with_credential_status():
    return SocialAccount.objects.defer("access_token", "refresh_token").annotate(
        has_vault_access_token=Q(access_token__startswith=VAULT_PREFIX),
        has_vault_refresh_token=Q(refresh_token__startswith=VAULT_PREFIX),
    )


@transaction.atomic
def access_token(account):
    account = SocialAccount.objects.select_for_update().get(pk=account.pk)
    if needs_reconnect(account):
        raise ProviderError("Reconnect this account before publishing.")
    if account.expires_at and account.expires_at <= timezone.now() + timedelta(
        minutes=2
    ):
        tokens = get_connection(account.platform).refresh_token(account.refresh_token)
        account.access_token = tokens["access_token"]
        account.refresh_token = tokens.get("refresh_token") or account.refresh_token
        account.expires_at = timezone.now() + timedelta(
            seconds=int(tokens.get("expires_in", 3600))
        )
        account.save(update_fields=["access_token", "refresh_token", "expires_at"])
    return account.access_token
