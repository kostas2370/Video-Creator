import logging
from contextlib import contextmanager

import requests
from django.db import DatabaseError, transaction

from apps.common.provider_errors import ProviderRequestError, provider_failure

from .models import ApiKeys, Provider

logger = logging.getLogger(__name__)


def save_warning(user, provider, rejected):
    if user is None or provider not in ApiKeys.FIELDS:
        return
    try:
        with transaction.atomic():
            keys, _ = ApiKeys.objects.select_for_update().get_or_create(user=user)
            warnings = {**keys.key_warnings, provider: True}
            if not rejected:
                warnings.pop(provider)
            if warnings != keys.key_warnings:
                ApiKeys.objects.filter(pk=keys.pk).update(key_warnings=warnings)
    except DatabaseError:
        logger.warning("Could not save the provider key warning")


def provider_request(method, url, *, user, provider, **kwargs):
    response = requests.request(method, url, **kwargs)
    status = response.status_code
    if status == 401 or 200 <= status < 300:
        save_warning(user, provider, status == 401)
    return response


def unauthorized(error):
    seen = set()
    while isinstance(error, BaseException) and id(error) not in seen:
        seen.add(id(error))
        status = (
            getattr(error, "status_code", None)
            or getattr(getattr(error, "response", None), "status_code", None)
            or getattr(error, "code", None)
        )
        if (
            status == 401
            or isinstance(error, ProviderRequestError)
            and error.code == "credentials"
        ):
            return True
        error = error.__cause__ or error.__context__
    return False


@contextmanager
def key_request(user, provider, api_key=None):
    try:
        yield api_key or ApiKeys.key_for(user, provider)
    except Exception as error:
        if unauthorized(error):
            save_warning(user, provider, True)
        failure = provider_failure(error) if provider == Provider.OPENAI else None
        if failure and not isinstance(error, ProviderRequestError):
            raise ProviderRequestError(failure["code"]) from error
        raise
    else:
        save_warning(user, provider, False)


def openai_request(user=None, api_key=None):
    return key_request(user, Provider.OPENAI, api_key)
