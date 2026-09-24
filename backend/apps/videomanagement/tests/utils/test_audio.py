from unittest.mock import patch

from django.test import TestCase

from ...baker_recipes import scene, video, voice_model
from ...models import Scene
from ...utils import audio_utils
from ...utils.audio_utils import make_scene_speech, make_scenes_speech, update_scene


class MakeSceneSpeechTests(TestCase):
    def setUp(self):
        self.voice = voice_model.make()
        self.video = video.make()

    def test_synthesises_the_line_and_hangs_it_on_the_scene(self):
        with patch.object(audio_utils, "save", return_value="dialogues/a.wav") as save:
            scene = make_scene_speech(self.video, " hello ", is_last=True)

        self.assertEqual(scene.file, "dialogues/a.wav")
        self.assertEqual(scene.text, "hello")
        self.assertTrue(scene.is_last)
        self.assertEqual(save.call_args.args[1], " hello ")

    def test_still_creates_the_scene_when_nothing_is_narrated(self):
        with patch.object(audio_utils, "save") as save:
            scene = make_scene_speech(self.video, "hello", False, narrate=False)

        save.assert_not_called()
        self.assertFalse(scene.file)
        self.assertEqual(Scene.objects.count(), 1)


class MakeScenesSpeechTests(TestCase):
    def setUp(self):
        self.video = video.make()
        self.video.gpt_answer = {
            "scenes": [
                {
                    "sentences": [
                        {"sentence": "one", "image_description": "a cat"},
                        {"sentence": "two", "image_description": "a dog"},
                    ]
                },
                {"sentences": [{"sentence": "three", "image_description": "a bird"}]},
            ]
        }

    def narrate(self):
        with patch.object(audio_utils, "narrate_scene") as spoken:
            make_scenes_speech(self.video)

        return spoken

    def lines(self):
        return list(self.video.scenes.order_by("id"))

    def test_makes_a_scene_for_every_sentence_of_every_scene(self):
        self.narrate()

        self.assertEqual([line.text for line in self.lines()], ["one", "two", "three"])

    def test_marks_only_the_last_sentence_of_each_scene_as_last(self):
        self.narrate()

        self.assertEqual([line.is_last for line in self.lines()], [False, True, True])

    def test_narrates_every_line_it_made(self):
        self.assertEqual(self.narrate().call_count, 3)

    def test_says_nothing_aloud_when_narration_is_off(self):
        self.video.settings = dict(narration=False)

        self.narrate().assert_not_called()
        self.assertEqual(len(self.lines()), 3)

    def test_narrates_by_default_when_the_setting_is_absent(self):
        self.video.settings = {}

        self.assertEqual(self.narrate().call_count, 3)


class UpdateSceneTests(TestCase):
    def test_resynthesises_the_line_and_saves_the_new_file(self):
        narrated = video.make(avatar=None)
        line = scene.make(video=narrated)

        with (
            patch.object(audio_utils, "ApiSyn"),
            patch.object(audio_utils, "save", return_value="dialogues/new.wav") as save,
        ):
            update_scene(line)

        line.refresh_from_db()
        self.assertEqual(line.file, "dialogues/new.wav")
        self.assertEqual(save.call_args.args[1], line.text)
