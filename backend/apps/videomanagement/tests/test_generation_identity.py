from unittest.mock import patch

from django.test import TestCase

from apps.videomanagement.baker_recipes import scene, video
from apps.videomanagement.models import SceneImage
from apps.videomanagement.services.scenes.narration import (
    ensure_scene_rows,
    make_scenes_speech,
)
from apps.videomanagement.services.scenes.visuals import create_image_scenes


class ScriptIdentityTests(TestCase):
    def setUp(self):
        self.video = video.make(
            mode="AI",
            settings={"narration": False},
            gpt_answer={
                "scenes": [
                    {
                        "sentences": [
                            {
                                "sentence": "Again.",
                                "image_description": "A red door",
                                "shot_plan": {"subject_action": "Open the door"},
                            },
                            {
                                "sentence": "Again.",
                                "image_description": "A blue door",
                                "shot_plan": {"subject_action": "Close the door"},
                            },
                        ]
                    }
                ]
            },
        )

    def test_duplicate_dialogue_has_distinct_rows_and_plans_and_resumes_by_identity(
        self,
    ):
        _, rows = ensure_scene_rows(self.video)
        self.assertNotEqual(rows[0].pk, rows[1].pk)
        self.assertEqual(rows[0].shot_plan["subject_action"], "Open the door")
        self.assertEqual(rows[1].shot_plan["subject_action"], "Close the door")
        rows[1].text = "Edited dialogue"
        rows[1].save(update_fields=["text"])
        _, resumed = ensure_scene_rows(self.video)
        self.assertEqual(
            [row.pk for row in resumed.values()], [row.pk for row in rows.values()]
        )
        self.assertEqual(resumed[1].text, "Edited dialogue")
        self.assertEqual(self.video.scenes.count(), 2)

    def test_legacy_collapsed_scene_is_reused_and_missing_occurrence_is_created(self):
        old = scene.make(video=self.video, text="Again.")
        _, rows = ensure_scene_rows(self.video)
        self.assertEqual(rows[0].pk, old.pk)
        self.assertNotEqual(rows[1].pk, old.pk)
        _, resumed = ensure_scene_rows(self.video)
        self.assertEqual(rows, resumed)

    def test_each_occurrence_gets_its_own_narration(self):
        self.video.settings = {"narration": True}
        with (
            patch(
                "apps.videomanagement.services.scenes.narration.stored_file_exists",
                return_value=False,
            ),
            patch(
                "apps.videomanagement.services.scenes.narration.narrate_scene"
            ) as narrate,
        ):
            make_scenes_speech(self.video)
        self.assertEqual(narrate.call_count, 2)
        self.assertNotEqual(
            narrate.call_args_list[0].args[0].pk, narrate.call_args_list[1].args[0].pk
        )

    def test_visual_resume_does_not_reuse_another_occurrences_asset(self):
        _, rows = ensure_scene_rows(self.video)
        SceneImage.objects.create(
            scene=rows[0], file="media/red.png", prompt="A red door"
        )
        with (
            patch(
                "apps.videomanagement.services.scenes.visuals.stored_file_exists",
                side_effect=lambda field: bool(field),
            ),
            patch(
                "apps.videomanagement.services.scenes.visuals.ImageProviderRegistry.resolve",
                return_value=lambda *a, **kw: "media/blue.png",
            ),
        ):
            create_image_scenes(self.video, mode="AI", provider="OPENAI")
        self.assertEqual(rows[0].scene_images.count(), 1)
        self.assertEqual(rows[1].scene_images.get().prompt, "A blue door")

    def test_adding_duplicate_dialogue_attaches_visual_to_new_scene(self):
        from apps.videomanagement.services.scenes.generation import create_scene

        old = scene.make(video=self.video, text="Again.")
        with patch(
            "apps.videomanagement.services.scenes.visuals.ImageProviderRegistry.resolve",
            return_value=lambda *a, **kw: "media/new.png",
        ):
            added = create_scene(
                self.video, {"text": "Again.", "image_description": "New shot"}, {}
            )
        self.assertNotEqual(old.pk, added.pk)
        self.assertFalse(old.scene_images.exists())
        self.assertEqual(added.scene_images.get().prompt, "New shot")
