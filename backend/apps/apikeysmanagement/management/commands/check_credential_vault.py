from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError

from apps.common.credential_encryption import (
    CredentialEncryptionError,
    decrypt_credential,
    encrypt_credential,
)


class Command(BaseCommand):
    help = "Verify that the configured Vault can encrypt and decrypt credentials."

    def handle(self, *args, **options):
        probe = uuid4().hex
        context = "viddie.credential_vault_check"
        try:
            result = decrypt_credential(encrypt_credential(probe, context), context)
        except CredentialEncryptionError:
            raise CommandError(
                "Vault could not verify an encryption round trip."
            ) from None
        if result != probe:
            raise CommandError(
                "Vault encryption round trip returned a different value."
            )
        self.stdout.write("Vault encryption and decryption verified.")
