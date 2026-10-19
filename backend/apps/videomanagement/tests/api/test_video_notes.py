from django.urls import reverse
from .base import ApiTestCase
from apps.usermanagement.baker_recipes import user


class VideoNotesTests(ApiTestCase):
    def save_notes(self, video, notes, previous=""):
        return self.client.patch(reverse("video-notes", args=[video.pk]),
            {"notes": notes, "previous_notes": previous}, format="json")

    def test_notes_round_trip_and_clear_without_affecting_render_state(self):
        video = self.video_for(status="COMPLETED")
        original_settings, original_time = video.settings.copy(), video.updated_at
        text = "Opening: keep it short.\n\nTry Poppins for captions.  "
        response = self.save_notes(video, text)
        self.assertEqual(response.status_code, 200, response.data)
        video.refresh_from_db()
        self.assertEqual(video.notes, text)
        self.assertEqual(video.status, "COMPLETED")
        self.assertEqual(video.settings, original_settings)
        self.assertEqual(video.updated_at, original_time)
        detail = self.client.get(reverse("video-detail", args=[video.pk]))
        self.assertEqual(detail.data["notes"], text)
        self.assertNotIn("notes", self.client.get(reverse("video-list")).data["results"][0])
        self.assertEqual(self.save_notes(video, "", text).status_code, 200)
        video.refresh_from_db()
        self.assertEqual(video.notes, "")
        self.scene_queue.assert_not_called()

    def test_notes_can_be_saved_while_rendering(self):
        video = self.video_for(status="RENDERING")
        self.assertEqual(self.save_notes(video, "Review after export").status_code, 200)
        video.refresh_from_db()
        self.assertEqual(video.status, "RENDERING")

    def test_foreign_video_and_oversized_notes_are_rejected(self):
        video = self.video_for(owner=user.make())
        self.assertEqual(self.save_notes(video, "Not mine").status_code, 404)
        owned = self.video_for()
        self.assertEqual(self.save_notes(owned, "x" * 10001).status_code, 400)
        owned.refresh_from_db()
        self.assertEqual(owned.notes, "")

    def test_stale_save_keeps_newer_notes_and_allows_retry_of_successful_save(self):
        video = self.video_for(notes="Newer notes")
        conflict = self.save_notes(video, "My stale draft")
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.data["notes"], "Newer notes")
        video.refresh_from_db()
        self.assertEqual(video.notes, "Newer notes")
        self.assertEqual(self.save_notes(video, "Newer notes").status_code, 200)
