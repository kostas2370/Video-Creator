from django.test import TestCase

from ..baker_recipes import (
    avatar,
    music,
    template_prompt,
    video,
    voice_model,
)
from ..models import UserPrompt, Video, VoiceModel


class VideoDefaultsTests(TestCase):
    def test_a_new_video_points_at_no_voice_rather_than_at_row_1(self):
        fresh = Video.objects.create(
            title="cats", prompt=UserPrompt.objects.create(prompt="cats")
        )

        self.assertIsNone(fresh.voice_model_id)
        self.assertIsNone(fresh.voice_model)

    def test_each_video_gets_its_own_settings_dict(self):
        first, second = Video(), Video()

        self.assertIsNot(first.settings, second.settings)

        first.settings["subtitles"] = True

        self.assertFalse(second.settings["subtitles"])
        self.assertFalse(Video().settings["subtitles"])


class GptAnswerTests(TestCase):
    def test_the_script_survives_a_round_trip_through_the_database(self):
        script = {
            "title": "Cats",
            "scenes": [
                {
                    "scene": "one",
                    "sentences": [{"sentence": "hello", "image_description": "a cat"}],
                }
            ],
        }
        made = video.make(gpt_answer=script)

        reloaded = Video.objects.get(pk=made.pk)

        self.assertEqual(reloaded.gpt_answer, script)
        self.assertEqual(reloaded.gpt_answer["scenes"][0]["scene"], "one")


    def test_a_video_with_no_script_reloads_as_none(self):
        made = video.make(gpt_answer=None)

        self.assertIsNone(Video.objects.get(pk=made.pk).gpt_answer)


class SelectVoiceTests(TestCase):
    def test_picks_one_of_the_voices_on_file(self):
        voices = voice_model.make(_quantity=3)

        self.assertIn(VoiceModel.select_voice(), voices)


class StringRepresentationTests(TestCase):
    """Names the admin lists rows by."""

    def test_models_are_named_by_the_field_a_person_would_recognise(self):
        for recipe, attribute in (
            (template_prompt, "title"),
            (music, "name"),
            (voice_model, "name"),
            (avatar, "name"),
            (video, "title"),
        ):
            instance = recipe.prepare()
            with self.subTest(model=type(instance).__name__):
                self.assertEqual(str(instance), getattr(instance, attribute))


class UUIDOrderingTests(TestCase):
    def test_scene_and_visual_order_does_not_depend_on_uuid_value(self):
        from uuid import UUID
        from datetime import timedelta
        from django.utils import timezone
        from ..models import Scene, SceneImage

        made = video.make()
        now = timezone.now()
        first = Scene.objects.create(video=made, text="First", id=UUID(int=99), created_at=now)
        second = Scene.objects.create(video=made, text="Second", id=UUID(int=1), created_at=now + timedelta(seconds=1))
        older = SceneImage.objects.create(scene=first, id=UUID(int=99), created_at=now)
        newer = SceneImage.objects.create(scene=first, id=UUID(int=1), created_at=now + timedelta(seconds=1))
        self.assertEqual(list(made.scenes.all()), [first, second])
        self.assertEqual(list(first.scene_images.all()), [older, newer])
        self.assertEqual(made.pk.version, 4)


class BackgroundRemovalMigrationTests(TestCase):
    def test_existing_review_parameters_keep_working_without_background(self):
        from importlib import import_module
        from types import SimpleNamespace
        from django.apps import apps
        from django.db import connection

        existing = video.make(status="REVIEW", settings={"generation_params": {"background": None, "message": "Keep this story", "music": "music-url"}, "narration": True})
        migration = import_module("apps.videomanagement.migrations.0025_remove_backgrounds")
        migration.remove_saved_background_parameters(apps, SimpleNamespace(connection=connection))
        existing.refresh_from_db()
        self.assertEqual(existing.settings, {"generation_params": {"message": "Keep this story", "music": "music-url"}, "narration": True})
