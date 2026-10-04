from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class ReviewMigrationTests(TransactionTestCase):
    def test_existing_provider_and_duplicate_login_rows_survive_migration(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        previous = [
            ("usermanagement", "0004_alter_login_ip"),
            (
                "apikeysmanagement",
                "0007_usercustomttsprovider_extra_parameters_and_more",
            ),
        ]
        executor.migrate(previous)
        old_apps = executor.loader.project_state(previous).apps
        User = old_apps.get_model("usermanagement", "User")
        Login = old_apps.get_model("usermanagement", "Login")
        Provider = old_apps.get_model("apikeysmanagement", "UserCustomTTSProvider")
        owner = User.objects.create(
            username="migration-owner", email="owner@example.test"
        )
        other = User.objects.create(
            username="migration-other", email="other@example.test"
        )
        first = Login.objects.create(user=owner, ip="192.0.2.1", count=2)
        Login.objects.create(user=owner, ip=first.ip, count=3)
        untouched = Login.objects.create(user=other, ip=first.ip, count=7)
        provider = Provider.objects.create(
            user=owner,
            name="Existing provider",
            endpoint_url="https://example.test/tts",
        )
        before = timezone.now()
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        apps = executor.loader.project_state(latest).apps
        Login = apps.get_model("usermanagement", "Login")
        Provider = apps.get_model("apikeysmanagement", "UserCustomTTSProvider")
        merged = Login.objects.get(user_id=owner.pk, ip=first.ip)
        self.assertEqual(merged.pk, first.pk)
        self.assertEqual(merged.count, 5)
        self.assertEqual(merged.date, first.date)
        self.assertEqual(Login.objects.get(pk=untouched.pk).count, 7)
        migrated = Provider.objects.get(pk=provider.pk)
        self.assertEqual(migrated.endpoint_url, provider.endpoint_url)
        self.assertGreaterEqual(migrated.created_at, before)
        self.assertGreaterEqual(migrated.updated_at, before)
