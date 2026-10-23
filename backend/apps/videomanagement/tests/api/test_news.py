from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from ...models import NewsUpdate


class NewsUpdateApiTests(TestCase):
    def setUp(self):
        NewsUpdate.objects.all().delete()
        self.client = APIClient()
        self.endpoint = reverse("news-list")

    def test_public_feed_excludes_drafts_and_scheduled_updates(self):
        now = timezone.now()
        older = NewsUpdate.objects.create(
            title="Earlier update", content="First release.",
            status=NewsUpdate.Status.PUBLISHED, published_at=now - timedelta(days=2),
        )
        latest = NewsUpdate.objects.create(
            title="Latest update", content="New features.\n\nMore details.",
            status=NewsUpdate.Status.PUBLISHED, published_at=now - timedelta(days=1),
        )
        draft = NewsUpdate.objects.create(title="Private draft", content="Not ready.")
        NewsUpdate.objects.create(
            title="Scheduled update", content="Not released yet.",
            status=NewsUpdate.Status.PUBLISHED, published_at=now + timedelta(days=1),
        )

        response = self.client.get(self.endpoint, {"status": "DRAFT"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(draft.status, NewsUpdate.Status.DRAFT)
        self.assertEqual(response.data["count"], 2)
        rows = response.data["results"]
        self.assertEqual([row["id"] for row in rows], [str(latest.pk), str(older.pk)])
        self.assertEqual(set(rows[0]), {"id", "title", "content", "published_at"})
        self.assertEqual(rows[0]["content"], latest.content)

    def test_news_is_public_read_only_even_with_an_expired_authorization_header(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer expired-token")
        self.assertEqual(self.client.get(self.endpoint).status_code, 200)
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    self.endpoint, {"title": "Unauthorized update"}, format="json"
                )
                self.assertEqual(response.status_code, 405)
        self.assertFalse(NewsUpdate.objects.exists())

    def test_older_updates_are_paginated_without_exposing_drafts(self):
        now = timezone.now()
        for index in range(12):
            NewsUpdate.objects.create(
                title=f"Update {index}", content="Release details.",
                status=NewsUpdate.Status.PUBLISHED,
                published_at=now - timedelta(days=index + 1),
            )
        NewsUpdate.objects.create(title="Hidden draft", content="Not public.")

        first = self.client.get(self.endpoint)
        second = self.client.get(self.endpoint, {"page": 2})

        self.assertEqual(len(first.data["results"]), 10)
        self.assertIsNotNone(first.data["next"])
        self.assertEqual(second.data["count"], 12)
        self.assertEqual(
            [row["title"] for row in second.data["results"]], ["Update 10", "Update 11"]
        )
        self.assertIsNone(second.data["next"])


class NewsSeedTests(TestCase):
    def test_seed_can_be_repeated_without_duplicating_or_overwriting_admin_edits(self):
        NewsUpdate.objects.all().delete()
        seed = import_module("apps.videomanagement.migrations.0046_seed_news_updates")
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
