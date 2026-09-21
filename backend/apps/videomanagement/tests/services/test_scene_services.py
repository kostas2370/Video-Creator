"""Adding, regenerating and updating a single scene."""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.exceptions import APIException, ValidationError


from ...baker_recipes import (
    scene,
    twitch_video,
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
        self.assertEqual(speech.call_args.args[3], "a new line")

    def test_attaches_an_uploaded_image_to_the_new_scene(self):
        line = scene.make(prompt=self.video.prompt)

        with patch.object(SceneServices, "make_scene_speech", return_value=line):
            create_scene(
                self.video,
                {"text": "a new line", "with_audio": True},
                files={"image": "media/images/uploaded.png"},
            )

        image = SceneImage.objects.get(scene=line)
        self.assertEqual(image.file, "media/images/uploaded.png")
        self.assertTrue(image.with_audio)

    def test_generates_an_image_when_one_was_described_instead(self):
        line = scene.make(prompt=self.video.prompt)

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

    def test_rejects_an_ai_scene_with_no_text(self):
        with self.assertRaises(ValidationError):
            create_scene(self.video, {"is_last": False}, files={})

    def test_adds_a_clip_to_a_twitch_video(self):
        video = twitch_video.make()
        client = MagicMock()
        client.get_clip_by_url.return_value = [{"title": "a clip"}]
        client.download_clip.return_value = "clips/raw.mp4"

        with (
            patch.object(SceneServices, "TwitchClient", return_value=client),
            patch.object(SceneServices, "create_twitch_clip_scene") as create,
        ):
            create_scene(video, {"url": "https://clips.twitch.tv/abc"}, files={})

        create.assert_called_once_with("clips/raw.mp4", "a clip", video.prompt)

    def test_rejects_a_twitch_scene_with_no_url(self):
        video = twitch_video.make()

        with self.assertRaises(ValidationError):
            create_scene(video, {"text": "a line"}, files={})

    def test_reports_a_twitch_clip_that_cannot_be_fetched(self):
        video = twitch_video.make()
        client = MagicMock()
        client.get_clip_by_url.side_effect = RuntimeError("gone")

        with patch.object(SceneServices, "TwitchClient", return_value=client):
            with self.assertRaises(APIException):
                create_scene(video, {"url": "https://clips.twitch.tv/abc"}, files={})
