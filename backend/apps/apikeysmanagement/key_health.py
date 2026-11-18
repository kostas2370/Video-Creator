import logging
from contextlib import contextmanager

from django.db import DatabaseError, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from apps.common.provider_errors import MESSAGES, ProviderRequestError, provider_failure

from .models import ApiKeys, Provider, ProviderKeyWarning

logger = logging.getLogger(__name__)


def key_fingerprint(key):
    return salted_hmac("openai-key-health", key, algorithm="sha256").hexdigest()


def openai_warning(key):
    warning = (
        ProviderKeyWarning.objects.filter(fingerprint=key_fingerprint(key)).first()
        if key
        else None
    )
    if warning and warning.code in MESSAGES:
        return {"code": warning.code, "message": MESSAGES[warning.code]}
    return None


def save_warning(key, code=None, *, before=None):
    if not key:
        return
    try:
        with transaction.atomic():
            fingerprint = key_fingerprint(key)
            if code in ("credentials", "quota", "access"):
                ProviderKeyWarning.objects.update_or_create(
                    fingerprint=fingerprint, defaults={"code": code}
                )
            elif code is None:
                ProviderKeyWarning.objects.filter(
                    fingerprint=fingerprint, updated_at__lte=before or timezone.now()
                ).delete()
    except DatabaseError:
        logger.warning("Could not update provider key health")


@contextmanager
def openai_request(user=None, api_key=None):
    key = api_key or ApiKeys.key_for(user, Provider.OPENAI)
    started_at = timezone.now()
    try:
        yield key
    except Exception as error:
        failure = provider_failure(error)
        if user is not None and failure:
            save_warning(key, failure["code"])
        if failure is None or isinstance(error, ProviderRequestError):
            raise
        raise ProviderRequestError(failure["code"]) from error
    else:
        if user is not None:
            save_warning(key, before=started_at)
