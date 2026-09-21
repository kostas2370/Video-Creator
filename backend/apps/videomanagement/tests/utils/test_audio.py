from unittest.mock import patch

from django.test import TestCase

from ...baker_recipes import scene, user_prompt, video, voice_model
from ...models import Scene
from ...utils import audio_utils
from ...utils.audio_utils import make_scene_speech, make_scenes_speech, update_scene


class MakeSceneSpeechTests(TestCase):
    def setUp(self):
        self.voice = voice_model.make()
        self.prompt = user_prompt.make()

    def test_synthesises_the_line_and_hangs_it_on_the_scene(self):
        with patch.object(audio_utils, "save", return_value="dialogues/a.wav") as save:
            scene = make_scene_speech(
                self.voice, "media/videos/v", self.prompt, " hello ", is_last=True
            )

        self.assertEqual(scene.file, "dialogues/a.wav")
        self.assertEqual(scene.text, "hello")
        self.assertTrue(scene.is_last)
        self.assertEqual(save.call_args.args[1], " hello ")

    def test_still_creates_the_scene_when_nothing_is_narrated(self):
        with patch.object(audio_utils, "save") as save:
            scene = make_scene_speech(
                self.voice, "media/videos/v", self.prompt, "hello", False, narrate=False
            )

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

    def test_narrates_every_sentence_of_every_scene(self):
        with patch.object(audio_utils, "make_scene_speech") as make:
            make_scenes_speech(self.video)

        self.assertEqual(make.call_count, 3)

    def test_marks_only_the_last_sentence_of_each_scene_as_last(self):
        with patch.object(audio_utils, "make_scene_speech") as make:
            make_scenes_speech(self.video)

        self.assertEqual(
            [call.args[4] for call in make.call_args_list], [False, True, True]
        )

    def test_passes_the_videos_narration_setting_down(self):
        self.video.settings = dict(narration=False)

        with patch.object(audio_utils, "make_scene_speech") as make:
            make_scenes_speech(self.video)

        self.assertIs(make.call_args.kwargs["narrate"], False)

    def test_narrates_by_default_when_the_setting_is_absent(self):
        self.video.settings = {}

        with patch.object(audio_utils, "make_scene_speech") as make:
            make_scenes_speech(self.video)

        self.assertIs(make.call_args.kwargs["narrate"], True)


class UpdateSceneTests(TestCase):
    def test_resynthesises_the_line_and_saves_the_new_file(self):
        narrated = video.make(avatar=None)
        line = scene.make(prompt=narrated.prompt)

        with (
            patch.object(audio_utils, "ApiSyn"),
            patch.object(audio_utils, "save", return_value="dialogues/new.wav") as save,
        ):
            update_scene(line)

        line.refresh_from_db()
        self.assertEqual(line.file, "dialogues/new.wav")
        self.assertEqual(save.call_args.args[1], line.text)
