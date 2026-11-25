import base64
import logging
import re
from pathlib import Path
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

logger = logging.getLogger(__name__)
VAULT_PREFIX = "viddie:vault:1:"


class CredentialEncryptionError(Exception):
    pass


def vault_request(operation, value, context):
    address = settings.CREDENTIAL_VAULT_URL
    if not address or not settings.CREDENTIAL_VAULT_TOKEN_FILE:
        raise CredentialEncryptionError(
            "Credential encryption service is not configured."
        )
    parsed = urlsplit(address)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise ImproperlyConfigured("CREDENTIAL_VAULT_URL must be an HTTPS origin.")
    mount = settings.CREDENTIAL_VAULT_MOUNT
    key = settings.CREDENTIAL_VAULT_KEY
    if not all(re.fullmatch(r"[a-zA-Z0-9_-]+", part) for part in (mount, key)):
        raise ImproperlyConfigured("Invalid credential Vault mount or key name.")
    try:
        token = Path(settings.CREDENTIAL_VAULT_TOKEN_FILE).read_text().strip()
        if not token:
            raise ValueError
        payload = {"context": base64.b64encode(context.encode()).decode()}
        if operation == "encrypt":
            payload["plaintext"] = base64.b64encode(value.encode()).decode()
        elif operation == "decrypt":
            payload["ciphertext"] = value
        else:
            raise ValueError
        with requests.Session() as session:
            session.trust_env = False
            response = session.post(
                f"{address.rstrip('/')}/v1/{mount}/{operation}/{key}",
                json=payload,
                headers={"X-Vault-Token": token},
                timeout=(3, 10),
                verify=settings.CREDENTIAL_VAULT_CA_BUNDLE or True,
                allow_redirects=False,
            )
            if response.status_code != 200:
                raise ValueError
            data = response.json()["data"]
            if operation == "encrypt":
                result = data["ciphertext"]
                if not isinstance(result, str) or not re.fullmatch(
                    r"vault:v[1-9][0-9]*:[A-Za-z0-9+/=]+", result
                ):
                    raise ValueError
            else:
                result = base64.b64decode(data["plaintext"], validate=True).decode()
    except (OSError, requests.RequestException, ValueError, TypeError, KeyError):
        logger.warning("Credential encryption service operation failed: %s", operation)
        raise CredentialEncryptionError(
            "Credential encryption service unavailable."
        ) from None
    logger.info("Credential encryption service operation succeeded: %s", operation)
    return result


def encrypt_credential(value, context):
    if value is None or value == "":
        return value
    return VAULT_PREFIX + vault_request("encrypt", value, context)


def decrypt_credential(value, context):
    if value is None or value == "":
        return value
    if value.startswith(VAULT_PREFIX):
        return vault_request("decrypt", value[len(VAULT_PREFIX) :], context)
    raise CredentialEncryptionError("Stored credential has an unsupported format.")


class CredentialFieldMixin:
    @property
    def encryption_context(self):
        return f"{self.model._meta.label_lower}.{self.name}"

    def from_db_value(self, value, expression, connection):
        return decrypt_credential(value, self.encryption_context)

    def get_db_prep_save(self, value, connection):
        if hasattr(value, "as_sql"):
            raise TypeError("Credential fields require a literal value.")
        return encrypt_credential(self.to_python(value), self.encryption_context)

    def get_internal_type(self):
        return "TextField"


class CredentialCharField(CredentialFieldMixin, models.CharField):
    pass


class CredentialTextField(CredentialFieldMixin, models.TextField):
    pass
