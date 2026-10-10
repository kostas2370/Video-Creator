from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ..baker_recipes import scene, scene_image, video
from ..services.SceneServices import draft_scene
from ..utils.audio_utils import ensure_scene_rows, make_scene_speech
from ..tasks import create_scene_task
from ..utils import scenes as scene_utils


class ScenePositionTests(TestCase):
    def test_inserting_in_the_middle_shifts_later_scenes_only(self):
        made, other = video.make(_quantity=2)
        first = scene.make(video=made, text="First")
        second = scene.make(video=made, text="Second")
        untouched = scene.make(video=other, text="Other")
        inserted = make_scene_speech(made, "Inserted", True, narrate=False, position=2)
        self.assertEqual(inserted.position, 2)
        self.assertEqual(list(made.scenes.values_list("text", "position")), [("First", 1), ("Inserted", 2), ("Second", 3)])
        untouched.refresh_from_db()
        self.assertEqual(untouched.position, 1)
        first.refresh_from_db()
        self.assertEqual(first.position, 1)

    def test_invalid_insert_position_leaves_existing_order_unchanged(self):
        made = video.make()
        scene.make(video=made, text="First")
        for position in (0, 3):
            with self.assertRaises(ValidationError):
                make_scene_speech(made, "Invalid", True, narrate=False, position=position)
        self.assertEqual(list(made.scenes.values_list("text", "position")), [("First", 1)])

    def test_batch_insertion_preserves_the_reviewed_order(self):
        made = video.make(status="GENERATION", voice_model=None)
        scene.make(video=made, text="First")
        scene.make(video=made, text="Last")
        create_scene_task(made.pk, {"position": 2, "scenes": [{"text": "Inserted A"}, {"text": "Inserted B"}]})
        self.assertEqual(list(made.scenes.values_list("text", "position")), [("First", 1), ("Inserted A", 2), ("Inserted B", 3), ("Last", 4)])
        made.refresh_from_db()
        self.assertEqual(made.status, "READY")

    def test_append_positions_are_scoped_to_each_video(self):
        first_video, second_video = video.make(_quantity=2)
        first = scene.make(video=first_video)
        second = scene.make(video=first_video)
        other = scene.make(video=second_video)
        self.assertEqual((first.position, second.position, other.position), (1, 2, 1))
        first.delete()
        appended = scene.make(video=first_video)
        self.assertEqual(appended.position, 3)

    def test_positions_override_creation_time(self):
        made = video.make()
        now = timezone.now()
        second = scene.make(video=made, text="Second", position=2, created_at=now)
        first = scene.make(video=made, text="First", position=1, created_at=now + timedelta(days=1))
        self.assertEqual(list(made.scenes.all()), [first, second])
        first.text = "Edited"
        first.save()
        self.assertEqual(first.position, 1)
        self.assertEqual(list(made.scenes.all()), [first, second])

    def test_duplicate_positions_are_rejected_within_a_video(self):
        made = video.make()
        scene.make(video=made, position=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            scene.make(video=made, position=1)

    def test_script_generation_assigns_positions_and_resume_keeps_them(self):
        made = video.make(gpt_answer={"scenes": [{"sentences": [
            {"sentence": "First", "image_description": "A beach"},
            {"sentence": "Second", "image_description": "A mountain"},
        ]}]})
        ensure_scene_rows(made)
        rows = list(made.scenes.values_list("text", "position"))
        ensure_scene_rows(made)
        self.assertEqual(rows, [("First", 1), ("Second", 2)])
        self.assertEqual(list(made.scenes.values_list("text", "position")), rows)

    def test_continuation_and_draft_context_follow_position(self):
        made = video.make(mode="AI")
        now = timezone.now()
        second = scene.make(video=made, text="Second", position=2, created_at=now)
        first = scene.make(video=made, text="First", position=1, created_at=now + timedelta(days=1))
        image = scene_image.make(scene=first, file="media/first.mp4")
        with patch.object(scene_utils, "stored_file_exists", return_value=True), patch.object(scene_utils, "continuation_frame", return_value="last.png") as frame:
            self.assertEqual(scene_utils.scene_reference(second, made, "sora"), "last.png")
        frame.assert_called_once_with(made, first.text, image.file.path)
        with patch("apps.videomanagement.services.SceneServices.get_update_sentence", return_value='{"text":"New", "image_description":"A forest"}') as generate:
            draft_scene(made, "Continue", use_context=True)
        prompt = generate.call_args.args[0]
        self.assertLess(prompt.index('"text": "First"'), prompt.index('"text": "Second"'))


class ScenePositionMigrationTests(TransactionTestCase):
    migrate_from = [("videomanagement", "0019_alter_scene_options_alter_sceneimage_options_and_more")]
    migrate_to = [("videomanagement", "0020_scene_position")]

    def test_backfill_keeps_existing_order_separately_for_each_video(self):
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(leaves))
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps
        OldScene = old_apps.get_model("videomanagement", "Scene")
        first_video, other_video = video.make(_quantity=2)
        now = timezone.now()
        second = OldScene.objects.create(video_id=first_video.pk, text="Second", created_at=now)
        first = OldScene.objects.create(video_id=first_video.pk, text="First", created_at=now - timedelta(days=1))
        other = OldScene.objects.create(video_id=other_video.pk, text="Other", created_at=now)
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        NewScene = executor.loader.project_state(self.migrate_to).apps.get_model("videomanagement", "Scene")
        self.assertEqual(NewScene.objects.get(pk=first.pk).position, 1)
        self.assertEqual(NewScene.objects.get(pk=second.pk).position, 2)
        self.assertEqual(NewScene.objects.get(pk=other.pk).position, 1)
        self.assertEqual(list(NewScene.objects.filter(video_id=first_video.pk).values_list("text", flat=True)), ["First", "Second"])
