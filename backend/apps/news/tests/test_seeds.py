from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase

from ..models import NewsUpdate


class NewsSeedTests(TestCase):
    def test_creation_news_is_ordered_and_keeps_existing_posts_and_corrections(self):
        seed = import_module("apps.news.migrations.0004_seed_creation_news")
        NewsUpdate.objects.all().delete()
        existing = NewsUpdate.objects.create(title="Existing post", content="Keep me.")
        editor = SimpleNamespace(connection=connection)

        seed.seed_updates(apps, editor)

        created = NewsUpdate.objects.exclude(pk=existing.pk)
        self.assertEqual(
            list(created.values_list("title", flat=True)),
            [row[1] for row in seed.UPDATES],
        )
        self.assertEqual(created.filter(status=NewsUpdate.Status.PUBLISHED).count(), 4)
        update = created.first()
        update.content = "An administrator's correction"
        update.status = NewsUpdate.Status.DRAFT
        update.save()

        seed.seed_updates(apps, editor)

        self.assertEqual(NewsUpdate.objects.count(), 5)
        update.refresh_from_db()
        existing.refresh_from_db()
        self.assertEqual(update.content, "An administrator's correction")
        self.assertEqual(update.status, NewsUpdate.Status.DRAFT)
        self.assertEqual(existing.content, "Keep me.")

    def test_seed_can_be_repeated_without_duplicating_or_overwriting_admin_edits(self):
        NewsUpdate.objects.all().delete()
        seed = import_module("apps.news.migrations.0002_seed_news_updates")
        editor = SimpleNamespace(connection=connection)
        seed.seed_updates(apps, editor)
        self.assertEqual(NewsUpdate.objects.count(), 6)

        update = NewsUpdate.objects.first()
        update.title = "Edited by an administrator"
        update.content = "Updated announcement."
        update.status = NewsUpdate.Status.DRAFT
        update.save()

        seed.seed_updates(apps, editor)

        self.assertEqual(NewsUpdate.objects.count(), 6)
        update.refresh_from_db()
        self.assertEqual(update.title, "Edited by an administrator")
        self.assertEqual(update.content, "Updated announcement.")
        self.assertEqual(update.status, NewsUpdate.Status.DRAFT)

    def test_beta_news_preserves_existing_updates_and_admin_edits_when_repeated(self):
        seed = import_module("apps.news.migrations.0003_seed_hosted_beta_news")
        NewsUpdate.objects.all().delete()
        existing = NewsUpdate.objects.create(
            title="Existing news", content="Keep this."
        )
        editor = SimpleNamespace(connection=connection)

        seed.seed_updates(apps, editor)

        self.assertEqual(NewsUpdate.objects.count(), 3)
        update = NewsUpdate.objects.exclude(pk=existing.pk).first()
        self.assertEqual(update.status, NewsUpdate.Status.PUBLISHED)
        published_at = update.published_at
        update.title = "An administrator's correction"
        update.content = "Edited release notes."
        update.status = NewsUpdate.Status.DRAFT
        update.save()

        seed.seed_updates(apps, editor)

        self.assertEqual(NewsUpdate.objects.count(), 3)
        update.refresh_from_db()
        existing.refresh_from_db()
        self.assertEqual(update.title, "An administrator's correction")
        self.assertEqual(update.content, "Edited release notes.")
        self.assertEqual(update.status, NewsUpdate.Status.DRAFT)
        self.assertEqual(update.published_at, published_at)
        self.assertEqual(existing.content, "Keep this.")
