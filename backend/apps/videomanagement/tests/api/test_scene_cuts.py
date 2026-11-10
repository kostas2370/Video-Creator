from django.urls import reverse
from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import scene
from .base import ApiTestCase


class SceneCutsTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for(settings={"narration": False, "subtitles": False})
        self.scene = scene.make(video=self.video, audio_settings={"duration": 10})
        self.url = reverse("scene-cuts", args=[self.scene.pk])
        self.payload = {
            "source_duration": 10,
            "previous": {},
            "sections": [{"start": 1, "end": 3}, {"start": 7, "end": 10}],
        }

    def test_saves_cuts_and_preview_uses_source_timing(self):
        response = self.client.patch(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["timing"]["duration"], 5)
        self.assertEqual(response.data["timing"]["source_duration"], 10)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.cuts["sections"], self.payload["sections"])
        preview = self.client.get(reverse("video-preview", args=[self.video.pk]))
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data["playback_sections"], self.payload["sections"])
        self.assertEqual(preview.data["duration"], 10)
        self.assertEqual(
            self.client.patch(self.url, self.payload, format="json").status_code, 409
        )
        # Duration edits invalidate saved source coordinates.
        response = self.client.patch(
            reverse("scene-timing", args=[self.scene.pk]),
            {"duration": 8},
            format="json",
        )
        self.assertEqual(response.data["timing"]["duration"], 8)
        preview = self.client.get(reverse("video-preview", args=[self.video.pk]))
        self.assertEqual(preview.data["playback_sections"], [{"start": 0, "end": 8}])

    def test_rejects_invalid_empty_overlapping_or_out_of_order_sections(self):
        for sections in (
            [],
            [{"start": 1, "end": 11}],
            [{"start": 4, "end": 3}],
            [{"start": 1, "end": 1.01}],
            [{"start": 0, "end": 3}, {"start": 2, "end": 4}],
            [{"start": "NaN", "end": 4}],
        ):
            response = self.client.patch(
                self.url, {**self.payload, "sections": sections}, format="json"
            )
            self.assertEqual(response.status_code, 400, response.data)
        response = self.client.patch(
            self.url, {**self.payload, "source_duration": 11}, format="json"
        )
        self.assertEqual(response.status_code, 409)

    def test_blocks_other_owners_and_in_progress_video_edits(self):
        foreign = scene.make(video=self.video_for(owner=user.make()))
        self.assertEqual(
            self.client.patch(
                reverse("scene-cuts", args=[foreign.pk]), self.payload, format="json"
            ).status_code,
            403,
        )
        for state in ("GENERATION", "RENDERING", "REVIEW"):
            self.video.status = state
            self.video.save()
            self.assertEqual(
                self.client.patch(self.url, self.payload, format="json").status_code,
                409,
            )
