from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import scene, scene_image
from .base import ApiTestCase


class VideoLibraryTests(ApiTestCase):
    def test_preview_uses_scene_order_and_skips_empty_visuals(self):
        video = self.video_for()
        opening = scene.make(video=video)
        later = scene.make(video=video)
        scene_image.make(scene=later, file="media/images/later.png")
        scene_image.make(scene=opening, file="")
        scene_image.make(scene=opening, file="media/images/opening.png")
        response = self.client.get(reverse("video-list"))
        self.assertEqual(response.status_code, 200)
        preview = response.data["results"][0]["preview_media"]
        self.assertEqual(preview["type"], "image")
        self.assertTrue(preview["url"].endswith("/media/images/opening.png"))

    def test_video_visuals_and_projects_without_media(self):
        with_clip = self.video_for()
        scene_image.make(
            scene=scene.make(video=with_clip), file="media/images/gameplay.mp4"
        )
        blank = self.video_for(video_type="MANUAL")
        response = self.client.get(reverse("video-list"))
        rows = {row["id"]: row for row in response.data["results"]}
        self.assertEqual(rows[str(with_clip.pk)]["preview_media"]["type"], "video")
        self.assertIsNone(rows[str(blank.pk)]["preview_media"])

    def test_status_filter_keeps_results_scoped_to_the_owner(self):
        completed = self.video_for(status="COMPLETED")
        self.video_for(status="READY")
        foreign = self.video_for(owner=user.make(), status="COMPLETED")
        scene_image.make(
            scene=scene.make(video=foreign), file="media/images/private.png"
        )
        response = self.client.get(reverse("video-list"), {"status": "COMPLETED"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(completed.pk))
        self.assertNotIn("private.png", str(response.data))

    def test_preview_query_count_does_not_grow_with_library_size(self):
        first = self.video_for()
        scene_image.make(scene=scene.make(video=first))
        with CaptureQueriesContext(connection) as small:
            self.assertEqual(self.client.get(reverse("video-list")).status_code, 200)
        for _ in range(5):
            scene_image.make(scene=scene.make(video=self.video_for()))
        with CaptureQueriesContext(connection) as larger:
            self.assertEqual(self.client.get(reverse("video-list")).status_code, 200)
        self.assertEqual(len(larger), len(small))
