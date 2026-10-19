from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.usermanagement.baker_recipes import user

from ...models import Video
from .base import ApiTestCase


class VideoFilterTests(ApiTestCase):
    def ids(self, **filters):
        response = self.client.get(reverse("video-list"), filters)
        self.assertEqual(response.status_code, 200, response.data)
        return [row["id"] for row in response.data["results"]]

    def test_project_types_separate_story_from_manual_and_handle_legacy_settings(self):
        ai = self.video_for(settings={})
        legacy = self.video_for(settings=None)
        manual = self.video_for(video_type="MANUAL", settings={})
        story = self.video_for(video_type="MANUAL", settings={"creation_mode": "STORY"})
        self.assertCountEqual(
            self.ids(creation_mode="AI"), [str(ai.pk), str(legacy.pk)]
        )
        self.assertEqual(self.ids(creation_mode="MANUAL"), [str(manual.pk)])
        self.assertEqual(self.ids(creation_mode="STORY"), [str(story.pk)])
        self.assertCountEqual(
            self.ids(video_type="MANUAL"), [str(manual.pk), str(story.pk)]
        )

    def test_combined_filters_search_and_owner_scope(self):
        match = self.video_for(
            title="Dog story",
            video_type="MANUAL",
            is_favorite=True,
            status="COMPLETED",
            settings={"creation_mode": "STORY"},
        )
        self.video_for(
            title="Dog story",
            video_type="MANUAL",
            status="COMPLETED",
            settings={"creation_mode": "STORY"},
        )
        self.video_for(title="Dog story", is_favorite=True, status="COMPLETED")
        self.video_for(
            owner=user.make(),
            title="Dog story",
            video_type="MANUAL",
            is_favorite=True,
            status="COMPLETED",
            settings={"creation_mode": "STORY"},
        )
        self.assertEqual(
            self.ids(
                search="dog",
                status="COMPLETED",
                creation_mode="STORY",
                is_favorite="true",
            ),
            [str(match.pk)],
        )
        self.assertEqual(self.ids(search="cat", is_favorite="true"), [])

    def test_favorites_can_be_filtered_both_ways(self):
        favorite = self.video_for(is_favorite=True)
        regular = self.video_for()
        self.assertEqual(self.ids(is_favorite="true"), [str(favorite.pk)])
        self.assertEqual(self.ids(is_favorite="false"), [str(regular.pk)])
        self.assertCountEqual(self.ids(), [str(favorite.pk), str(regular.pk)])

    def test_sorting_uses_edit_time_by_default_and_supports_creation_and_title(self):
        older = self.video_for(title="Alpha")
        newer = self.video_for(title="Beta")
        now = timezone.now()
        Video.objects.filter(pk=older.pk).update(
            created_at=now - timedelta(days=2), updated_at=now
        )
        Video.objects.filter(pk=newer.pk).update(
            created_at=now - timedelta(days=1), updated_at=now - timedelta(hours=1)
        )
        self.assertEqual(self.ids(), [str(older.pk), str(newer.pk)])
        self.assertEqual(
            self.ids(ordering="-created_at"), [str(newer.pk), str(older.pk)]
        )
        self.assertEqual(
            self.ids(ordering="created_at"), [str(older.pk), str(newer.pk)]
        )
        self.assertEqual(self.ids(ordering="title"), [str(older.pk), str(newer.pk)])
        self.assertEqual(self.ids(ordering="-title"), [str(newer.pk), str(older.pk)])

    def test_equal_sort_values_have_deterministic_order(self):
        videos = [self.video_for(title="Same") for _ in range(3)]
        self.assertEqual(self.ids(ordering="title"), sorted(str(v.pk) for v in videos))

    def test_invalid_choices_return_validation_errors(self):
        for filters in (
            {"creation_mode": "unknown"},
            {"status": "unknown"},
            {"video_type": "unknown"},
            {"ordering": "prompt__prompt"},
        ):
            with self.subTest(filters=filters):
                self.assertEqual(
                    self.client.get(reverse("video-list"), filters).status_code, 400
                )

    def test_favorite_action_round_trip_preserves_render_state_and_edit_time(self):
        video = self.video_for(status="RENDERING")
        original_time, original_settings = video.updated_at, video.settings.copy()
        url = reverse("video-favorite", args=[video.pk])
        for value in (True, True, False):
            response = self.client.patch(url, {"is_favorite": value}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            video.refresh_from_db()
            self.assertEqual(video.is_favorite, value)
            self.assertEqual(video.updated_at, original_time)
            self.assertEqual(video.status, "RENDERING")
            self.assertEqual(video.settings, original_settings)
            detail = self.client.get(reverse("video-detail", args=[video.pk]))
            self.assertEqual(detail.data["is_favorite"], value)
            row = next(
                row
                for row in self.client.get(reverse("video-list")).data["results"]
                if row["id"] == str(video.pk)
            )
            self.assertEqual(row["is_favorite"], value)
        self.scene_queue.assert_not_called()

    def test_favorites_reject_foreign_anonymous_and_invalid_requests(self):
        foreign = self.video_for(owner=user.make())
        self.assertEqual(
            self.client.patch(
                reverse("video-favorite", args=[foreign.pk]),
                {"is_favorite": True},
                format="json",
            ).status_code,
            404,
        )
        owned = self.video_for()
        url = reverse("video-favorite", args=[owned.pk])
        for payload in ({}, {"is_favorite": "invalid"}, {"is_favorite": None}):
            self.assertEqual(
                self.client.patch(url, payload, format="json").status_code, 400
            )
        owned.refresh_from_db()
        self.assertFalse(owned.is_favorite)
        self.client.force_authenticate(None)
        self.assertIn(
            self.client.patch(url, {"is_favorite": True}, format="json").status_code,
            [401, 403],
        )
