from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from ..models import NewsUpdate


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
