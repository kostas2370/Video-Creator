from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.models import Value
from django.test import TestCase
from django.urls import reverse

from apps.common.credential_encryption import VAULT_PREFIX, CredentialEncryptionError
from apps.publishing.models import SocialAccount
from apps.usermanagement.baker_recipes import superuser, user

from ..models import ApiKeys, UserCustomTTSProvider, UserCustomVisualProvider


class CredentialMigrationTests(TestCase):
    def setUp(self):
        scratch = TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        old_key = Fernet.generate_key()
        self.keyfile = Path(scratch.name, "legacy-key")
        self.keyfile.write_bytes(old_key)
        self.old = Fernet(old_key)
        self.user = user.make()

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

    def legacy_credential(self, obj, field, value):
        return self.raw_credential(
            obj, field, self.old.encrypt(value.encode()).decode()
        )

    def migrate(self, *args, **kwargs):
        output = StringIO()
        call_command("migrate_credentials", *args, stdout=output, **kwargs)
        return output.getvalue()

    def test_vault_only_runtime_and_verified_migration_cover_every_credential_model(
        self,
    ):
        owner = self.user
        rows = [
            (ApiKeys.objects.create(user=owner), "openai_key"),
            (UserCustomTTSProvider.objects.create(user=owner, name="tts"), "api_key"),
            (
                UserCustomVisualProvider.objects.create(user=owner, name="visual"),
                "api_key",
            ),
            (
                SocialAccount.objects.create(
                    user=owner, platform="youtube", external_id="test"
                ),
                "refresh_token",
            ),
        ]
        secret = "test-credential-α"
        old_values = [self.legacy_credential(obj, field, secret) for obj, field in rows]
        with self.assertRaises(CredentialEncryptionError):
            ApiKeys.objects.get(pk=rows[0][0].pk)
        with self.assertRaisesMessage(CommandError, "Legacy credentials remain"):
            self.migrate("--verify")

        dry = self.migrate("--legacy-key-file", str(self.keyfile))
        self.assertIn("legacy 4; migrated 0", dry)
        self.assertEqual([self.raw_credential(*row) for row in rows], old_values)
        applied = self.migrate(
            "--legacy-key-file", str(self.keyfile), "--apply", "--batch-size", "1"
        )
        self.assertIn("legacy 4; migrated 4", applied)
        self.assertNotIn(secret, applied)

        self.keyfile.unlink()
        self.assertIn("legacy 0; migrated 0", self.migrate("--verify"))
        for obj, field in rows:
            self.assertTrue(self.raw_credential(obj, field).startswith(VAULT_PREFIX))
            self.assertEqual(getattr(type(obj).objects.get(pk=obj.pk), field), secret)

    def test_wrong_key_leaves_old_ciphertext_unchanged(self):
        keys = ApiKeys.objects.create(user=self.user)
        old = self.legacy_credential(keys, "openai_key", "test-credential")
        self.keyfile.write_bytes(Fernet.generate_key())

        with self.assertRaisesMessage(CommandError, "this row was not changed"):
            self.migrate("--legacy-key-file", str(self.keyfile), "--apply")

        self.assertEqual(self.raw_credential(keys, "openai_key"), old)

    def test_sql_expressions_cannot_store_plaintext_credentials(self):
        keys = ApiKeys.objects.create(user=self.user)
        with self.assertRaisesMessage(TypeError, "require a literal value"):
            ApiKeys.objects.filter(pk=keys.pk).update(
                openai_key=Value("test-credential")
            )

    def test_admin_can_view_metadata_without_decrypting_or_editing_keys(self):
        keys = ApiKeys.objects.create(user=self.user)
        self.legacy_credential(keys, "openai_key", "test-credential")
        self.client.force_login(superuser.make())
        url = reverse("admin:apikeysmanagement_apikeys_change", args=[keys.pk])
        with patch("apps.common.credential_encryption.vault_request") as vault:
            response = self.client.get(url)
            self.assertNotContains(response, "openai_key")
            self.assertEqual(
                self.client.post(url, {"openai_key": "replacement"}).status_code, 403
            )
        vault.assert_not_called()
