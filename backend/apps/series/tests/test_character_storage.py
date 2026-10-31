from uuid import uuid4

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.series.cast import replace_series_cast
from apps.series.creative import reference_approval
from apps.series.models import Character, VideoSeries
from apps.videomanagement.tests.api.base import ApiTestCase


class CharacterStorageTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.series = VideoSeries.objects.create(
            created_by=self.user, title="Bananas", premise="A fruit story",
            visual_style="3D animation", narration=False,
        )
        self.cast = []
        for name in ("Bananito", "Bananita", "Bruno"):
            character = Character.objects.create(
                created_by=self.user, name=name, appearance="Yellow banana",
                visual_style=self.series.visual_style, status="READY",
                image=f"media/characters/{uuid4().hex}.png",
            )
            data = {
                "id": str(character.pk), "name": name, "appearance": "Yellow banana",
                "wardrobe": "", "personality": "Curious", "relationships": "Friends",
                "reference_id": str(character.pk),
            }
            data["reference_approval"] = reference_approval(data, self.series.visual_style)
            self.cast.append(data)
        replace_series_cast(self.series, self.cast)

    def test_reordering_keeps_the_same_three_characters_images_and_approvals(self):
        original = list(self.series.cast_members.values_list("pk", "image"))
        response = self.client.patch(
            reverse("series-detail", args=[self.series.pk]),
            {"cast": list(reversed(self.cast))}, format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["id"] for row in response.data["cast"]], [row["id"] for row in reversed(self.cast)])
        self.assertCountEqual(self.series.cast_members.values_list("pk", "image"), original)
        self.assertTrue(response.data["cast_ready"])
        self.assertEqual(Character.objects.count(), 3)
        self.assertTrue(all(character.image_approved for character in self.series.cast_members.all()))

    def test_editing_appearance_requires_renewed_approval(self):
        edited = {**self.cast[0], "appearance": "Blue banana"}
        response = self.client.patch(reverse("series-detail", args=[self.series.pk]), {"cast": [edited]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["cast_ready"])
        character = Character.objects.get(series=self.series)
        self.assertEqual(character.appearance, "Blue banana")
        self.assertFalse(character.image_approved)
        self.assertTrue(character.image)

    def test_list_queries_do_not_grow_with_the_number_of_characters(self):
        def query_count():
            with CaptureQueriesContext(connection) as captured:
                response = self.client.get(reverse("series-list"))
                self.assertEqual(response.status_code, 200)
            return len(captured)
        first = query_count()
        for index in range(3):
            series = VideoSeries.objects.create(created_by=self.user, title=f"Series {index}", premise="Fruit", visual_style="3D", narration=False)
            cast = [{**row, "id": str(uuid4()), "reference_id": row["id"]} for row in self.cast]
            for row in cast:
                row["reference_approval"] = reference_approval(row, series.visual_style)
            replace_series_cast(series, cast)
        self.assertEqual(query_count(), first)
