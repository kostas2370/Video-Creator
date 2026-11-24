from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from ..credential_encryption import (
    VAULT_PREFIX,
    CredentialEncryptionError,
    encrypt_credential,
)


@override_settings(
    CREDENTIAL_VAULT_URL="https://vault:8200",
    CREDENTIAL_VAULT_MOUNT="transit",
    CREDENTIAL_VAULT_KEY="viddie-credentials",
    CREDENTIAL_VAULT_CA_BUNDLE="/test/ca.pem",
)
class VaultTransportTests(SimpleTestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.token_file = Path(directory.name, "vault-token")
        self.token_file.write_text("test-vault-token")
        self.enterContext(
            override_settings(CREDENTIAL_VAULT_TOKEN_FILE=str(self.token_file))
        )

    def test_tls_transport_rejects_redirects_and_preserves_ciphertext_version(self):
        cipher = "vault:v2:czNjcjN0"
        response = Mock(status_code=200)
        response.json.return_value = {"data": {"ciphertext": cipher}}
        with patch("apps.common.credential_encryption.requests.Session") as session:
            client = session.return_value.__enter__.return_value
            client.post.return_value = response
            stored = encrypt_credential("test-secret", "field")

        self.assertEqual(stored, VAULT_PREFIX + cipher)
        self.assertFalse(client.trust_env)
        client.post.assert_called_once_with(
            "https://vault:8200/v1/transit/encrypt/viddie-credentials",
            json={"plaintext": "dGVzdC1zZWNyZXQ=", "context": "ZmllbGQ="},
            headers={"X-Vault-Token": "test-vault-token"},
            timeout=(3, 10),
            verify="/test/ca.pem",
            allow_redirects=False,
        )

    def test_a_failed_vault_request_never_falls_back_to_local_encryption(self):
        with (
            patch("apps.common.credential_encryption.requests.Session") as session,
            self.assertRaisesMessage(CredentialEncryptionError, "service unavailable"),
        ):
            client = session.return_value.__enter__.return_value
            client.post.return_value = Mock(status_code=307)
            encrypt_credential("test-secret", "field")
