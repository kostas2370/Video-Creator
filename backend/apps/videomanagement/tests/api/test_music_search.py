from unittest.mock import patch

from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from apps.videomanagement import draft_tasks
from apps.videomanagement.services.media import music_search

from .base import ApiTestCase


class MusicSearchApiTests(ApiTestCase):
    def test_recommendation_uses_the_owned_video_and_rejects_foreign_videos(self):
        video = self.video_for(status="READY")
        url = reverse("musiccatalogtrack-ai-recommend")
        response = self.client.post(url, {"video_id": str(video.pk)}, format="json")
        self.assertEqual(response.status_code, 202, response.data)
        with patch.object(
            music_search,
            "recommend_music_preferences",
            return_value={"preferences": "Soft piano"},
        ) as recommend:
            self.assertEqual(self.run_draft_task(), {"preferences": "Soft piano"})
        self.assertEqual(recommend.call_args.kwargs["video"], video)
        self.draft_queue.reset_mock()
        foreign = self.video_for(owner=user.make())
        self.assertEqual(
            self.client.post(
                url, {"video_id": str(foreign.pk)}, format="json"
            ).status_code,
            404,
        )
        self.draft_queue.assert_not_called()

    def test_previously_queued_recommendations_still_return_preferences(self):
        with patch.object(
            music_search,
            "recommend_music_preferences",
            return_value={"preferences": "Piano"},
        ) as recommend:
            result = draft_tasks.search_music_task.run(
                str(self.user.pk), prompt="Science", recommend_only=True
            )
        self.assertEqual(result, {"preferences": "Piano"})
        recommend.assert_called_once_with(self.user, video=None, prompt="Science")

    def test_queues_owned_music_search_and_returns_worker_results(self):
        video = self.video_for(status="READY")
        response = self.client.post(
            reverse("musiccatalogtrack-ai-search"),
            {"video_id": str(video.pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 202, response.data)
        with patch.object(
            music_search, "search_music", return_value={"brief": {}, "tracks": []}
        ) as search:
            self.assertEqual(self.run_draft_task(), {"brief": {}, "tracks": []})
        self.assertEqual(search.call_args.kwargs["video"], video)

    def test_search_can_use_a_generation_prompt_before_a_video_exists(self):
        response = self.client.post(
            reverse("musiccatalogtrack-ai-search"),
            {"prompt": "Science lesson", "preferences": "Piano"},
            format="json",
        )
        self.assertEqual(response.status_code, 202, response.data)
        with patch.object(music_search, "search_music", return_value={}) as search:
            self.run_draft_task()
        self.assertEqual(search.call_args.kwargs["prompt"], "Science lesson")
        self.assertIsNone(search.call_args.kwargs["video"])

    def test_foreign_video_and_empty_requests_never_queue_searches(self):
        foreign = self.video_for(owner=user.make())
        url = reverse("musiccatalogtrack-ai-search")
        self.assertEqual(
            self.client.post(
                url, {"video_id": str(foreign.pk)}, format="json"
            ).status_code,
            404,
        )
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 400)
        self.draft_queue.assert_not_called()

    def test_queues_import_only_for_owned_editable_video(self):
        video = self.video_for(status="READY")
        url = reverse("musiccatalogtrack-ai-import")
        foreign = self.video_for(owner=user.make(), status="READY")
        self.assertEqual(
            self.client.post(
                url,
                {"video_id": str(foreign.pk), "selection": "ai:abcdefghijk"},
                format="json",
            ).status_code,
            404,
        )
        response = self.client.post(
            url,
            {"video_id": str(video.pk), "selection": "ai:abcdefghijk"},
            format="json",
        )
        self.assertEqual(response.status_code, 202, response.data)
        with patch.object(
            music_search, "import_search_music", return_value=video
        ) as save:
            self.assertEqual(self.run_draft_task(), {"video_id": str(video.pk)})
        save.assert_called_once_with(video, "ai:abcdefghijk")
        self.draft_queue.reset_mock()
        video.status = "RENDERING"
        video.save()
        self.assertEqual(
            self.client.post(
                url,
                {"video_id": str(video.pk), "selection": "ai:abcdefghijk"},
                format="json",
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.post(
                url,
                {"video_id": str(video.pk), "selection": "http://invalid"},
                format="json",
            ).status_code,
            400,
        )
        self.draft_queue.assert_not_called()
