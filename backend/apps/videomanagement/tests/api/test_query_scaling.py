"""Keep editor response query counts independent of the number of scenes."""
from unittest.mock import patch

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from ...baker_recipes import intro, outro, scene, scene_image
from .base import ApiTestCase


class VideoQueryScalingTests(ApiTestCase):
    def make_video(self, count):
        video = self.video_for(
            settings={"narration": False},
            intro=intro.make(created_by=self.user),
            outro=outro.make(created_by=self.user),
        )
        for _ in range(count):
            scene_image.make(scene=scene.make(video=video))
        return video

    def query_count(self, video, action):
        with patch("apps.videomanagement.services.editing.publish_update"), CaptureQueriesContext(connection) as queries:
            if action == "update":
                response = self.client.patch(
                    reverse("video-detail", args=[video.pk]), {"title": "Updated"}, format="json"
                )
            elif action == "reorder":
                ids = list(video.scenes.values_list("pk", flat=True))
                response = self.client.post(
                    reverse("video-reorder-scenes", args=[video.pk]),
                    {"scene_ids": [str(pk) for pk in reversed(ids)]}, format="json",
                )
            else:
                response = self.client.get(reverse("video-detail", args=[video.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.data["video"] if action == "update" else response.data
        self.assertEqual(len(data["scenes"]), video.scenes.count())
        return len(queries)

    def test_editor_query_counts_do_not_grow_with_scene_count(self):
        small = self.make_video(2)
        large = self.make_video(20)
        for action in ("detail", "update", "reorder"):
            with self.subTest(action=action):
                small_count = self.query_count(small, action)
                large_count = self.query_count(large, action)
                print(f"QUERY SCALING {action}: 2 scenes={small_count}, 20 scenes={large_count}")
                self.assertEqual(large_count, small_count)
