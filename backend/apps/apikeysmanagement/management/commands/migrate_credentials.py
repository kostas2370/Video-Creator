import hmac
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction

from apps.common.credential_encryption import (
    VAULT_PREFIX,
    CredentialEncryptionError,
    CredentialFieldMixin,
    decrypt_credential,
    encrypt_credential,
)


class Command(BaseCommand):
    help = "Verify or migrate encrypted credentials to Vault; defaults to a dry run."

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--apply", action="store_true")
        mode.add_argument("--verify", action="store_true")
        mode.add_argument("--check-vault", action="store_true")
        parser.add_argument("--database", default="default")
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--legacy-key-file", type=Path)

    def handle(self, *args, **options):
        legacy_key_file = options["legacy_key_file"]
        legacy_crypter = None
        if legacy_key_file is not None:
            try:
                legacy_crypter = Fernet(Path(legacy_key_file).read_bytes().strip())
            except (OSError, ValueError):
                raise CommandError(
                    "Cannot load the legacy encryption key file."
                ) from None
        batch_size = options["batch_size"]
        if batch_size < 1:
            raise CommandError("Batch size must be positive.")
        probe = uuid4().hex
        probe_context = "viddie.credential_migration_check"
        try:
            if (
                decrypt_credential(
                    encrypt_credential(probe, probe_context), probe_context
                )
                != probe
            ):
                raise CredentialEncryptionError
        except CredentialEncryptionError:
            raise CommandError(
                "Vault could not verify an encryption round trip."
            ) from None
        if options["check_vault"]:
            self.stdout.write("Vault encryption and decryption verified.")
            return
        alias = options["database"]
        connection = connections[alias]
        quote = connection.ops.quote_name
        legacy_count = migrated_count = checked_count = 0
        for model in apps.get_models():
            fields = [
                field
                for field in model._meta.local_fields
                if isinstance(field, CredentialFieldMixin)
            ]
            if not fields:
                continue
            table = quote(model._meta.db_table)
            pk = quote(model._meta.pk.column)
            columns = ", ".join([pk, *(quote(field.column) for field in fields)])
            last_pk = None
            while True:
                clause = f"WHERE {pk} > %s" if last_pk is not None else ""
                params = [last_pk] if last_pk is not None else []
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"SELECT {columns} FROM {table} {clause} ORDER BY {pk} LIMIT %s",
                        [*params, batch_size],
                    )
                    rows = cursor.fetchall()
                if not rows:
                    break
                for row in rows:
                    updates = []
                    for field, stored in zip(fields, row[1:]):
                        if stored is None or stored == "":
                            continue
                        try:
                            if stored.startswith(VAULT_PREFIX):
                                decrypt_credential(stored, field.encryption_context)
                                checked_count += 1
                                continue
                            legacy_count += 1
                            if options["verify"]:
                                continue
                            if legacy_crypter is None:
                                raise CommandError(
                                    "Legacy credentials remain. Provide --legacy-key-file."
                                )
                            plain = legacy_crypter.decrypt(stored.encode()).decode()
                            checked_count += 1
                            replacement = encrypt_credential(
                                plain, field.encryption_context
                            )
                            verified = decrypt_credential(
                                replacement, field.encryption_context
                            )
                            if not hmac.compare_digest(
                                plain.encode(), verified.encode()
                            ):
                                raise CredentialEncryptionError
                            updates.append((field.column, stored, replacement))
                        except (CredentialEncryptionError, InvalidToken, UnicodeError):
                            raise CommandError(
                                f"Credential verification failed for {model._meta.label}.{field.name}; "
                                "this row was not changed. Previously completed rows remain migrated."
                            ) from None
                    if updates and options["apply"]:
                        assignments = ", ".join(
                            f"{quote(column)} = %s" for column, _, _ in updates
                        )
                        guards = " AND ".join(
                            f"{quote(column)} = %s" for column, _, _ in updates
                        )
                        with (
                            transaction.atomic(using=alias),
                            connection.cursor() as cursor,
                        ):
                            cursor.execute(
                                f"UPDATE {table} SET {assignments} WHERE {pk} = %s AND {guards}",
                                [
                                    *(new for _, _, new in updates),
                                    row[0],
                                    *(old for _, old, _ in updates),
                                ],
                            )
                            if cursor.rowcount != 1:
                                raise CommandError(
                                    "A credential changed concurrently; rerun the migration."
                                )
                        migrated_count += len(updates)
                last_pk = rows[-1][0]
        self.stdout.write(
            f"Verified {checked_count} credentials; legacy {legacy_count}; migrated {migrated_count}."
        )
        if options["verify"] and legacy_count:
            raise CommandError(
                "Legacy credentials remain; keep the old key and rerun with --apply."
            )
        if not options["apply"] and not options["verify"]:
            self.stdout.write(
                "Dry run only. No database records changed. Use --apply after reviewing backups."
            )
