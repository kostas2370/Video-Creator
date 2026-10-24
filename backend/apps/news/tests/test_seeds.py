from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase

from ..models import NewsUpdate


class NewsSeedTests(TestCase):
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
