from unittest.mock import patch

from django.urls import reverse
from rest_framework.exceptions import APIException

from apps.series.models import SeriesEpisode, VideoSeries
from apps.series.services.episodes import draft_episode_idea
from apps.usermanagement.baker_recipes import user
from apps.videomanagement.tests.api.base import ApiTestCase


class EpisodeIdeaTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.series = VideoSeries.objects.create(
            created_by=self.user, title="Milo", premise="A fox learns science",
            characters="Milo wears a teal scarf", visual_style="Watercolor woodland",
        )
        self.url = reverse("series-episode-idea", args=[self.series.pk])

    @patch("apps.series.services.episodes.get_update_sentence", return_value="  Milo discovers a frozen pond.  ")
    def test_queues_reviewable_idea_without_creating_an_episode(self, generate):
        response = self.client.post(self.url, {"idea": "Explore winter"}, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(self.run_draft_task(), {"idea": "Milo discovers a frozen pond."})
        prompt = generate.call_args.args[0]
        self.assertIn("A fox learns science", prompt)
        self.assertIn("Explore winter", prompt)
        self.assertEqual(SeriesEpisode.objects.count(), 0)

    def test_cannot_queue_or_execute_for_another_users_series(self):
        from apps.videomanagement.draft_tasks import draft_episode_idea_task
        self.series.created_by = user.make()
        self.series.save()
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 404)
        self.draft_queue.assert_not_called()
        with self.assertRaises(VideoSeries.DoesNotExist):
            draft_episode_idea_task.run(str(self.user.pk), series_id=str(self.series.pk))

    def test_rejects_oversized_starting_idea(self):
        response = self.client.post(self.url, {"idea": "x" * 2001}, format="json")
        self.assertEqual(response.status_code, 400)
        self.draft_queue.assert_not_called()

    def test_invalid_provider_output_never_becomes_an_idea(self):
        for result in (None, {}, "  ", "x" * 2001):
            with self.subTest(result=str(result)[:20]), patch(
                "apps.series.services.episodes.get_update_sentence", return_value=result
            ):
                with self.assertRaises(APIException):
                    draft_episode_idea(self.series, owner=self.user)
        self.assertFalse(self.series.episodes.exists())

    @patch("apps.series.services.episodes.get_update_sentence", return_value="A fresh discovery")
    def test_uses_only_reviewed_canon_memories(self, generate):
        for number, summary, canon, reviewed in (
            (1, "Reviewed discovery", True, True),
            (2, "Stale discovery", True, False),
            (3, "Unprepared discovery", False, True),
        ):
            episode = SeriesEpisode.objects.create(
                series=self.series, video=self.video_for(status="READY"),
                number=number, idea="Earlier story", summary=summary,
                is_canon=canon,
            )
            if reviewed:
                episode.memory_source_hash = episode.script_hash
                episode.save(update_fields=["memory_source_hash"])
        draft_episode_idea(self.series, owner=self.user)
        prompt = generate.call_args.args[0]
        self.assertIn("Reviewed discovery", prompt)
        self.assertNotIn("Stale discovery", prompt)
        self.assertNotIn("Unprepared discovery", prompt)
