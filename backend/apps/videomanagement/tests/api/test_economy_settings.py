from unittest.mock import patch

from django.urls import reverse

from .base import ApiTestCase


class EconomySettingsTests(ApiTestCase):
    def test_economy_requires_explicit_selection_and_does_not_generate_media(self):
        video = self.video_for(settings={"narration": True})
        with patch(
            "apps.videomanagement.services.videos.settings.update_scene"
        ) as narrate:
            response = self.client.patch(
                reverse("video-detail", args=[video.pk]),
                {"generation_mode": "ECONOMY"},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        video.refresh_from_db()
        self.assertEqual(video.settings["generation_mode"], "ECONOMY")
        self.assertTrue(video.settings["narration"])
        narrate.assert_not_called()
        self.assertFalse(self.scene_queue.called)

    def test_invalid_modes_and_processing_projects_are_rejected(self):
        video = self.video_for()
        endpoint = reverse("video-detail", args=[video.pk])
        self.assertEqual(
            self.client.patch(
                endpoint, {"generation_mode": "invalid"}, format="json"
            ).status_code,
            400,
        )
        video.status = "GENERATION"
        video.save()
        self.assertEqual(
            self.client.patch(
                endpoint, {"generation_mode": "ECONOMY"}, format="json"
            ).status_code,
            409,
        )
