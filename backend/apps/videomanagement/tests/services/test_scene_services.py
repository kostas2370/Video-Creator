"""Adding, regenerating and updating a single scene."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.exceptions import APIException, ValidationError


from ...baker_recipes import (
    scene,
    video,
)
from ...models import SceneImage
from ...services import (
    SceneServices,
)
from ...services.SceneServices import create_scene, generate_scene, update_scene


class GenerateSceneTests(TestCase):
    def test_asks_the_model_for_a_rewrite(self):
        line = scene.make(text="the old line")

        with patch.object(
            SceneServices, "get_update_sentence", return_value="a new line"
        ) as rewrite:
            self.assertEqual(generate_scene("make it funnier", line), "a new line")

        self.assertIn("the old line", rewrite.call_args.args[0])

    def test_does_not_call_the_model_when_the_text_is_unchanged(self):
        line = scene.make(text=" the old line ")

        with patch.object(SceneServices, "get_update_sentence") as rewrite:
            self.assertEqual(generate_scene("the old line", line), "the old line")

        rewrite.assert_not_called()


class UpdateSceneServiceTests(TestCase):
    def test_stores_the_new_text_and_resynthesises_the_line(self):
        line = scene.make(text="the old line")

        with patch.object(SceneServices, "update") as resynthesise:
            self.assertEqual(update_scene("a new line", line), "a new line")

        resynthesise.assert_called_once_with(line)

    def test_keeps_the_old_text_when_the_new_one_is_blank(self):
        line = scene.make(text="the old line")

        with patch.object(SceneServices, "update"):
            self.assertEqual(update_scene("", line), "the old line")


class CreateSceneTests(TestCase):
    def setUp(self):
        self.video = video.make()

    def test_adds_a_narrated_scene_to_an_ai_video(self):
        line = scene.prepare(text="a new line")

        with patch.object(
            SceneServices, "make_scene_speech", return_value=line
        ) as speech:
            created = create_scene(
                self.video, {"text": "a new line", "is_last": True}, files={}
            )

        self.assertIs(created, line)
        self.assertEqual(speech.call_args.args[1], "a new line")

    def test_attaches_an_uploaded_image_to_the_new_scene(self):
        line = scene.make(video=self.video)

        with patch.object(SceneServices, "make_scene_speech", return_value=line):
            create_scene(
                self.video,
                {"text": "a new line", "with_audio": True},
                files={"image": "media/images/uploaded.png"},
            )

        image = SceneImage.objects.get(scene=line)
        self.assertEqual(image.file, "media/images/uploaded.png")
        self.assertTrue(image.with_audio)

    def test_upload_does_not_also_generate_a_visual(self):
        line = scene.make(video=self.video)
        with (
            patch.object(SceneServices, "make_scene_speech", return_value=line),
            patch.object(SceneServices, "create_image_scene") as generate,
        ):
            create_scene(self.video, {"text": "A line", "image_description": "A sky"},
                         files={"image": "media/images/upload.png"})
        generate.assert_not_called()
        self.assertEqual(line.scene_images.count(), 1)

    def test_generates_an_image_when_one_was_described_instead(self):
        line = scene.make(video=self.video)

        with (
            patch.object(SceneServices, "make_scene_speech", return_value=line),
            patch.object(SceneServices, "create_image_scene") as generate,
        ):
            create_scene(
                self.video,
                {"text": "a new line", "image_description": "a cat"},
                files={},
            )

        self.assertEqual(generate.call_args.kwargs["image"], "a cat")

    def test_new_scenes_inherit_the_saved_visual_provider_style_and_reference(self):
        self.video.mode = "AI"
        self.video.settings = {"provider": "sora", "style": "natural"}
        line = scene.make(video=self.video)
        with (
            patch.object(SceneServices, "make_scene_speech", return_value=line),
            patch.object(SceneServices, "scene_reference", return_value="images/context.png") as reference,
            patch.object(SceneServices, "create_image_scene") as generate,
        ):
            create_scene(self.video, {"text": "Next sentence.", "image_description": "Same character."}, files={})
        reference.assert_called_once_with(line, self.video, "sora")
        self.assertEqual(generate.call_args.kwargs["provider"], "sora")
        self.assertEqual(generate.call_args.kwargs["style"], "natural")
        self.assertEqual(generate.call_args.kwargs["reference"], "images/context.png")

    def test_rejects_an_ai_scene_with_no_text(self):
        with self.assertRaises(ValidationError):
            create_scene(self.video, {"is_last": False}, files={})


class DraftSceneTests(TestCase):
    def test_a_section_returns_the_requested_short_scenes_without_saving(self):
        from ...services.SceneServices import draft_scene
        import json

        vid = video.make()
        drafts = [{"text": f"Sentence {index}.", "image_description": "A path"} for index in range(3)]
        with patch.object(SceneServices, "get_update_sentence", return_value=json.dumps({"scenes": drafts})) as generate:
            result = draft_scene(vid, "Continue", draft_type="section", sentence_count=3)
        self.assertEqual(result["scenes"], drafts)
        self.assertIn("exactly 3", generate.call_args.args[0])
        self.assertFalse(vid.scenes.exists())

    def test_rejects_an_oversized_sentence_or_incorrect_scene_count(self):
        from ...services.SceneServices import draft_scene
        import json

        vid = video.make()
        for result in (
            {"scenes": [{"text": "Too few.", "image_description": "A path"}]},
            {"scenes": [{"text": "x" * 321, "image_description": "A path"}] * 3},
        ):
            with self.subTest(result=result), patch.object(SceneServices, "get_update_sentence", return_value=json.dumps(result)):
                with self.assertRaises(APIException):
                    draft_scene(vid, "Continue", draft_type="story", sentence_count=3)
        self.assertFalse(vid.scenes.exists())

    def test_context_contains_every_current_scene_and_visual_in_order(self):
        from ...services.SceneServices import draft_scene

        vid = video.make(title="Journey")
        first = scene.make(video=vid, text="Edited opening")
        scene.make(video=vid, text="Current ending")
        SceneImage.objects.create(scene=first, prompt="Mountain sunrise")
        other = scene.make(text="Another user's story")
        with patch.object(SceneServices, "get_update_sentence", return_value='{"text":"Next line","image_description":"A trail"}') as generate:
            result = draft_scene(vid, "Continue the journey", True)
        prompt = generate.call_args.args[0]
        for text in ("Journey", "Edited opening", "Current ending", "Mountain sunrise"):
            self.assertIn(text, prompt)
        self.assertLess(prompt.index("Edited opening"), prompt.index("Current ending"))
        self.assertNotIn(other.text, prompt)
        self.assertEqual(generate.call_args.kwargs["user"], vid.created_by)
        self.assertEqual(result["text"], "Next line")
        self.assertEqual(vid.scenes.count(), 2)

    def test_without_context_excludes_all_video_content(self):
        from ...services.SceneServices import draft_scene

        vid = video.make(title="Private title")
        scene.make(video=vid, text="Private dialogue")
        with patch.object(SceneServices, "get_update_sentence", return_value='```json\n{"text":"New line","image_description":"A trail"}\n```') as generate:
            draft_scene(vid, "An independent scene", False)
        prompt = generate.call_args.args[0]
        self.assertIn("An independent scene", prompt)
        self.assertNotIn("Private title", prompt)
        self.assertNotIn("Private dialogue", prompt)

    def test_rejects_invalid_model_output_without_creating_a_scene(self):
        from ...services.SceneServices import draft_scene

        vid = video.make()
        for reply in ('not json', '{}', '{"text":42,"image_description":"sky"}', '{"text":" ","image_description":"sky"}'):
            with self.subTest(reply=reply), patch.object(SceneServices, "get_update_sentence", return_value=reply):
                with self.assertRaises(APIException):
                    draft_scene(vid, "Next scene")
        self.assertFalse(vid.scenes.exists())
