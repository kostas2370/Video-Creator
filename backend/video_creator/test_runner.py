import base64
from contextlib import ExitStack
from secrets import token_bytes
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import requests
from django.test.runner import DiscoverRunner
from django.test.utils import override_settings

from apps.apikeysmanagement.models import ApiKeys


class ServiceKeysRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._resources = ExitStack()

        keys = {
            setting: f"test-{setting.lower()}" for _, setting in ApiKeys.FIELDS.values()
        }
        vault_token = self._resources.enter_context(NamedTemporaryFile())
        vault_token.write(b"test-vault-token")
        vault_token.flush()
        self._resources.enter_context(
            override_settings(
                **keys,
                CREDENTIAL_VAULT_URL="https://vault.test",
                CREDENTIAL_VAULT_MOUNT="transit",
                CREDENTIAL_VAULT_KEY="viddie-credentials",
                CREDENTIAL_VAULT_TOKEN_FILE=vault_token.name,
                CREDENTIAL_VAULT_CA_BUNDLE="",
            )
        )
        ciphertexts = {}

        real_post = requests.Session.post

        def test_vault_post(session, url, *args, **kwargs):
            if not url.startswith("https://vault.test/v1/transit/"):
                return real_post(session, url, *args, **kwargs)
            payload = kwargs["json"]
            response = requests.Response()
            if "/encrypt/" in url:
                ciphertext = "vault:v1:" + base64.b64encode(token_bytes(32)).decode()
                ciphertexts[ciphertext, payload["context"]] = payload["plaintext"]
                data = {"ciphertext": ciphertext}
            else:
                plaintext = ciphertexts.get((payload["ciphertext"], payload["context"]))
                if plaintext is None:
                    response.status_code = 400
                    return response
                data = {"plaintext": plaintext}
            response.status_code = 200
            response.json = lambda: {"data": data}
            return response

        self._resources.enter_context(
            patch.object(requests.Session, "post", test_vault_post)
        )

    def teardown_test_environment(self, **kwargs):
        self._resources.close()
        super().teardown_test_environment(**kwargs)
