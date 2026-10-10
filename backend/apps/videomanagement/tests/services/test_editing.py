from django.test import TestCase

from ...baker_recipes import scene, video
from ...models import Video
from ...services.editing import reorder_scenes, update_scene_transition
from ...services.VideoServices import video_update
from ...utils.exceptions import VideoEditConflict


class EditingServiceTests(TestCase):
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
