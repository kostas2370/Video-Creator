from datetime import timedelta
from importlib import import_module

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class MoveNewsAppTests(TransactionTestCase):
    old_target = [("videomanagement", "0046_seed_news_updates"), ("news", None)]
    new_target = [("news", "0002_move_news_table")]

    def tearDown(self):
        # Always return the test database to the current schema, even if an
        # assertion fails while testing the older migration state.
        MigrationExecutor(connection).migrate(self.new_target)
        super().tearDown()

    def test_move_preserves_entries_seed_edits_and_admin_permissions(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.old_target)
        legacy_apps = executor.loader.project_state(
            [("videomanagement", "0046_seed_news_updates")]
        ).apps
        LegacyNews = legacy_apps.get_model("videomanagement", "NewsUpdate")
        LegacyNews.objects.all().delete()
        seed = import_module("apps.videomanagement.migrations.0046_seed_news_updates")
        with connection.schema_editor() as editor:
            seed.seed_updates(legacy_apps, editor)
        edited = LegacyNews.objects.first()
        edited.title = "Edited by an administrator"
        edited.content = "Custom announcement."
        edited.status = "DRAFT"
        edited.published_at = timezone.now() - timedelta(days=1)
        edited.save()
        with connection.schema_editor() as editor:
            seed.seed_updates(legacy_apps, editor)
        before = list(LegacyNews.objects.order_by("id").values())
        self.assertEqual(len(before), 6)

        content_type, _ = ContentType.objects.get_or_create(
            app_label="videomanagement", model="newsupdate"
        )
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type, codename="change_newsupdate",
            defaults={"name": "Can change news update"},
        )
        editors = Group.objects.create(name="News editors")
        editors.permissions.add(permission)

        executor = MigrationExecutor(connection)
        executor.migrate(self.new_target)
        News = executor.loader.project_state(self.new_target).apps.get_model("news", "NewsUpdate")

        self.assertEqual(list(News.objects.order_by("id").values()), before)
        moved = News.objects.get(pk=edited.pk)
        self.assertEqual(moved.title, "Edited by an administrator")
        self.assertEqual(moved.status, "DRAFT")
        content_type.refresh_from_db()
        self.assertEqual(content_type.app_label, "news")
        self.assertTrue(editors.permissions.filter(pk=permission.pk).exists())
        self.assertIn("news_newsupdate", connection.introspection.table_names())
        self.assertNotIn("videomanagement_newsupdate", connection.introspection.table_names())
