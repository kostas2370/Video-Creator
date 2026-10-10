from uuid import uuid4
from unittest.mock import patch

from django.db import connection
from django.http import Http404
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from ...baker_recipes import scene, video
from ...models import Video
from ...services.editing import editable_video, reorder_scenes, update_scene_transition
from ...services.VideoServices import video_update
from ...utils.exceptions import VideoEditConflict


class EditingServiceTests(TestCase):
    def test_exception_inside_the_context_rolls_back_the_edit(self):
        made = video.make(status="READY", title="Original")
        with self.assertRaises(RuntimeError):
            with editable_video(made.pk) as locked:
                locked.title = "Changed"
                locked.save(update_fields=["title"])
                raise RuntimeError("Edit failed")
        made.refresh_from_db()
        self.assertEqual(made.title, "Original")

    def test_missing_video_is_reported_as_not_found(self):
        with self.assertRaises(Http404):
            with editable_video(uuid4()):
                self.fail("A missing video cannot be edited")

    def test_unchanged_order_and_transition_do_not_write_or_publish(self):
        made = video.make(status="READY")
        first, second = scene.make(video=made, _quantity=2)
        with patch("apps.videomanagement.services.editing.publish_update") as publish:
            with CaptureQueriesContext(connection) as queries:
                reorder_scenes(made, [first.pk, second.pk])
                update_scene_transition(first, transition_after="DEFAULT", transition_duration=None)
        publish.assert_not_called()
        self.assertFalse(any(query["sql"].lstrip().upper().startswith("UPDATE") for query in queries))

    def test_reorder_query_count_does_not_grow_with_each_scene(self):
        counts = []
        for size in (4, 30):
            made = video.make(status="READY")
            rows = scene.make(video=made, _quantity=size)
            ids = [row.pk for row in reversed(rows)]
            with CaptureQueriesContext(connection) as queries:
                reorder_scenes(made, ids)
            counts.append(len(queries))
            self.assertEqual(list(made.scenes.values_list("pk", flat=True)), ids)
            self.assertEqual(list(made.scenes.values_list("position", flat=True)), list(range(1, size + 1)))
        self.assertEqual(counts[0], counts[1])

    def test_stale_callers_cannot_edit_a_video_that_started_rendering(self):
        made = video.make(status="READY")
        first, second = scene.make(video=made, _quantity=2)
        Video.objects.filter(pk=made.pk).update(status="RENDERING")
        actions = (
            lambda: reorder_scenes(made, [second.pk, first.pk]),
            lambda: update_scene_transition(first, transition_after="CUT"),
            lambda: video_update(made, transition_default="CUT"),
        )
        for action in actions:
            with self.assertRaises(VideoEditConflict):
                action()
        self.assertEqual(list(made.scenes.values_list("pk", flat=True)), [first.pk, second.pk])
        first.refresh_from_db()
        self.assertEqual(first.transition_after, "DEFAULT")

    def test_reorder_rejects_a_duplicate_list_without_serializer_validation(self):
        made = video.make(status="READY")
        first, second = scene.make(video=made, _quantity=2)
        with self.assertRaises(VideoEditConflict):
            reorder_scenes(made, [first.pk, first.pk])
        self.assertEqual(list(made.scenes.values_list("pk", flat=True)), [first.pk, second.pk])

    def test_changing_style_preserves_an_omitted_duration_override(self):
        made = video.make(status="READY")
        line = scene.make(video=made, transition_duration=0.25)
        updated = update_scene_transition(line, transition_after="DISSOLVE")
        self.assertEqual(updated.transition_duration, 0.25)
        line.refresh_from_db()
        self.assertEqual(line.transition_after, "DISSOLVE")

    def test_stale_default_edit_preserves_current_video_settings(self):
        made = video.make(status="READY", settings={"narration": True})
        Video.objects.filter(pk=made.pk).update(settings={"narration": False})
        updated = video_update(made, transition_default="CUT")
        self.assertEqual(updated.settings, {"narration": False, "transition_default": "CUT"})
