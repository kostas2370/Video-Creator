from io import StringIO
from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.models import Value
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.common.credential_encryption import VAULT_PREFIX, CredentialEncryptionError
from apps.publishing.accounts import access_token, accounts_with_credential_status
from apps.publishing.models import SocialAccount
from apps.publishing.serializers import AccountSerializer
from apps.usermanagement.baker_recipes import superuser, user

from ..models import ApiKeys, Provider, UserCustomTTSProvider, UserCustomVisualProvider
from ..serializers import ApiKeysSerializer


class CredentialReplacementTests(TestCase):
    def setUp(self):
        self.user = user.make(use_service_api_keys=False)

    def raw_credential(self, obj, field, replacement=None):
        quote = connection.ops.quote_name
        table = quote(obj._meta.db_table)
        pk = quote(obj._meta.pk.column)
        column = quote(obj._meta.get_field(field).column)
        key = obj._meta.pk.get_db_prep_value(obj.pk, connection)
        with connection.cursor() as cursor:
            if replacement is not None:
                cursor.execute(
                    f"UPDATE {table} SET {column} = %s WHERE {pk} = %s",
                    [replacement, key],
                )
            cursor.execute(f"SELECT {column} FROM {table} WHERE {pk} = %s", [key])
            return cursor.fetchone()[0]

    def test_owner_can_replace_a_vault_key_without_exposing_either_value(self):
        keys = ApiKeys.objects.create(user=self.user, openai_key="test-existing-secret")
        replacement = "test-replacement-secret"
        serializer = ApiKeysSerializer(
            keys, data={"openai_key": replacement}, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertTrue(
            self.raw_credential(keys, "openai_key").startswith(VAULT_PREFIX)
        )
        self.assertEqual(ApiKeys.key_for(self.user, Provider.OPENAI), replacement)
        self.assertNotIn(replacement, serializer.data["openai_key"])
        self.assertNotIn("test-existing-secret", str(serializer.data))

    def test_custom_provider_secrets_are_stored_with_vault(self):
        for model in (UserCustomTTSProvider, UserCustomVisualProvider):
            with self.subTest(model=model):
                provider = model.objects.create(
                    user=self.user, name="example", api_key="test-custom-secret"
                )
                self.assertTrue(
                    self.raw_credential(provider, "api_key").startswith(VAULT_PREFIX)
                )
                provider.refresh_from_db()
                self.assertEqual(provider.api_key, "test-custom-secret")

    def test_publishing_status_does_not_decrypt_vault_tokens(self):
        account = SocialAccount.objects.create(
            user=self.user,
            platform="youtube",
            external_id="test",
            access_token="test-access-token",
            refresh_token="test-refresh-token",
            expires_at=timezone.now() + timedelta(days=1),
        )
        with patch("apps.common.credential_encryption.vault_request") as vault:
            listed = accounts_with_credential_status().get(pk=account.pk)
            self.assertFalse(AccountSerializer(listed).data["needs_reconnect"])
        vault.assert_not_called()
        self.assertEqual(access_token(account), "test-access-token")

    def test_unrecognized_stored_values_fail_closed(self):
        keys = ApiKeys.objects.create(user=self.user)
        self.raw_credential(keys, "openai_key", "unrecognized-test-value")
        with (
            patch("apps.common.credential_encryption.vault_request") as vault,
            self.assertRaisesMessage(CredentialEncryptionError, "unsupported format"),
        ):
            keys.refresh_from_db()
        vault.assert_not_called()

    def test_vault_preflight_performs_a_round_trip_without_reading_credentials(self):
        output = StringIO()
        with self.assertNumQueries(0):
            call_command("check_credential_vault", stdout=output)
        self.assertIn("Vault encryption and decryption verified.", output.getvalue())

    def test_vault_stand_in_survives_cleanup_of_individual_test_mocks(self):
        patch.stopall()
        output = StringIO()

        call_command("check_credential_vault", stdout=output)

        self.assertIn("Vault encryption and decryption verified.", output.getvalue())

    def test_vault_preflight_fails_if_vault_is_unavailable(self):
        with (
            patch(
                "apps.common.credential_encryption.vault_request",
                side_effect=CredentialEncryptionError,
            ),
            self.assertRaisesMessage(
                CommandError, "could not verify an encryption round trip"
            ),
        ):
            call_command("check_credential_vault")

    def test_sql_expressions_cannot_store_plaintext_credentials(self):
        keys = ApiKeys.objects.create(user=self.user)
        with self.assertRaisesMessage(TypeError, "require a literal value"):
            ApiKeys.objects.filter(pk=keys.pk).update(
                openai_key=Value("test-credential")
            )

    def test_admin_can_view_metadata_without_decrypting_or_editing_keys(self):
        keys = ApiKeys.objects.create(user=self.user)
        self.raw_credential(keys, "openai_key", "unsupported-test-value")
        self.client.force_login(superuser.make())
        url = reverse("admin:apikeysmanagement_apikeys_change", args=[keys.pk])
        with patch("apps.common.credential_encryption.vault_request") as vault:
            response = self.client.get(url)
            self.assertNotContains(response, "openai_key")
            self.assertEqual(
                self.client.post(url, {"openai_key": "replacement"}).status_code, 403
            )
        vault.assert_not_called()
