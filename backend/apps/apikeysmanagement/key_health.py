import logging
from contextlib import contextmanager

from django.db import DatabaseError, transaction

from apps.common.provider_errors import ProviderRequestError, provider_failure

from .models import ApiKeys, Provider

logger = logging.getLogger(__name__)


def save_warning(user, code=""):
    if user is None or code not in ("", "credentials", "quota", "access"):
        return
    try:
        with transaction.atomic():
            if code:
                ApiKeys.objects.get_or_create(user=user)
            ApiKeys.objects.filter(user=user).update(openai_warning=code)
    except DatabaseError:
        logger.warning("Could not save the OpenAI key warning")


@contextmanager
def openai_request(user=None, api_key=None):
    try:
        yield api_key or ApiKeys.key_for(user, Provider.OPENAI)
    except Exception as error:
        failure = provider_failure(error)
        if failure:
            save_warning(user, failure["code"])
        if failure is None or isinstance(error, ProviderRequestError):
            raise
        raise ProviderRequestError(failure["code"]) from error
    else:
        save_warning(user)
