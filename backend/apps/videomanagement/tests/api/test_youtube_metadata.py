from types import SimpleNamespace
from unittest.mock import patch

from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import scene

from .base import ApiTestCase

SERVICE = "apps.videomanagement.services.videos.youtube_metadata"


class YouTubeDescriptionTests(ApiTestCase):
    def draft(self, video, mode="generate"):
        return self.client.post(reverse("video-youtube-description", args=[video.pk]), {"mode": mode}, format="json")

    def test_generation_uses_edited_script_and_does_not_change_export(self):
        video = self.video_for(status="COMPLETED", title="Ocean life")
        scene.make(video=video, text="Whales migrate every year.")
        original = video.updated_at
        with patch(f"{SERVICE}.get_update_sentence", return_value="Learn about whale migration.") as generate:
            response = self.draft(video)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("Whales migrate", generate.call_args.args[0])
        self.assertEqual(generate.call_args.kwargs["user"], self.user)
        video.refresh_from_db()
        self.assertEqual(video.updated_at, original)
        self.assertEqual(video.status, "COMPLETED")
        self.scene_queue.assert_not_called()

    def test_template_uses_script_without_calling_ai(self):
        video = self.video_for()
        scene.make(video=video, text="An edited scene.")
        with patch(f"{SERVICE}.get_update_sentence") as generate:
            response = self.draft(video, "template")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("An edited scene.", response.data["description"])
        generate.assert_not_called()

    def test_chapters_use_timeline_offsets_and_merge_short_sections(self):
        video = self.video_for(status="COMPLETED")
        def segment(kind, start, text=""):
            return SimpleNamespace(kind=kind, start=start, content=SimpleNamespace(text=text))
        timeline = SimpleNamespace(duration=50, segments=[segment("intro", 0), segment("scene", 12, "Whales"), segment("scene", 17, "Short scene"), segment("scene", 30, "Reefs"), segment("outro", 47)])
        with patch(f"{SERVICE}.preview_timeline", return_value=timeline):
            response = self.draft(video, "timestamps")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["description"], "Chapters\n00:00 Intro\n00:12 Whales\n00:30 Reefs")

    def test_short_video_cannot_produce_misleading_chapters(self):
        video = self.video_for()
        with patch(f"{SERVICE}.preview_timeline", return_value=SimpleNamespace(duration=8, segments=[])):
            self.assertEqual(self.draft(video, "timestamps").status_code, 400)

    def test_rejects_empty_or_oversized_ai_output(self):
        video = self.video_for()
        scene.make(video=video, text="Whales migrate.")
        for reply in ("", "🐳" * 1200, "<invalid>"):
            with patch(f"{SERVICE}.get_update_sentence", return_value=reply):
                self.assertEqual(self.draft(video).status_code, 500)

    def test_other_users_video_is_not_accessible(self):
        self.assertEqual(self.draft(self.video_for(owner=user.make())).status_code, 404)

    def test_mode_is_validated(self):
        self.assertEqual(self.draft(self.video_for(), "unknown").status_code, 400)


class SavedVideoDetailsTests(ApiTestCase):
    def details(self, video):
        return {"title": video.title, "description": video.description, "tags": video.tags}

    def save(self, video, **changes):
        return self.client.patch(reverse("video-details", args=[video.pk]), {
            "title": "Edited title", "description": "A saved description.",
            "tags": {"youtube": ["ocean life"], "tiktok": ["OceanLife"], "search": ["ocean"]},
            "previous_details": self.details(video), **changes,
        }, format="json")

    def test_saves_all_details_and_preserves_completed_export(self):
        video = self.video_for(status="COMPLETED")
        original = video.updated_at
        response = self.save(video)
        self.assertEqual(response.status_code, 200, response.data)
        video.refresh_from_db()
        self.assertEqual(video.title, "Edited title")
        self.assertEqual(video.description, "A saved description.")
        self.assertEqual(video.tags["youtube"], ["ocean life"])
        self.assertEqual(video.status, "COMPLETED")
        self.assertEqual(video.updated_at, original)
        loaded = self.client.get(reverse("video-detail", args=[video.pk]))
        self.assertEqual(loaded.data["description"], "A saved description.")
        self.scene_queue.assert_not_called()

    def test_concurrent_edits_are_not_overwritten(self):
        video = self.video_for()
        baseline = self.details(video)
        self.assertEqual(self.save(video).status_code, 200)
        response = self.save(video, title="Another title", previous_details=baseline)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["details"]["title"], "Edited title")

    def test_saving_invalid_details_is_atomic(self):
        video = self.video_for()
        old = self.details(video)
        self.assertEqual(self.save(video, description="🐳" * 1251).status_code, 400)
        video.refresh_from_db()
        self.assertEqual(self.details(video), old)

    def test_cannot_edit_another_users_details(self):
        self.assertEqual(self.save(self.video_for(owner=user.make())).status_code, 404)
