"""Re-running a generation must not redo what already landed on disk."""

import os
import shutil
import uuid
from unittest.mock import patch

from django.conf import settings as django_settings
from django.test import TestCase

from slugify import slugify

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import video, voice_model
from ...models import Scene, SceneImage
from ...utils import scenes as scenes_utils
from ...utils.audio_utils import make_scenes_speech
from ...utils.scenes import create_image_scenes


def media_dir():
    return f"media/videos/resume-{uuid.uuid4()}"


A_SCRIPT = {
    "title": "Cats",
    "scenes": [
        {
            "scene": "one",
            "sentences": [
                {"sentence": "hello", "image_description": "a cat"},
                {"sentence": "goodbye", "image_description": "a door"},
            ],
        }
    ],
}


class ResumeNarrationTests(TestCase):
    def setUp(self):
        self.dir = media_dir()
        os.makedirs(f"{django_settings.BASE_DIR}/{self.dir}/dialogues", exist_ok=True)
        self.addCleanup(shutil.rmtree, f"{django_settings.BASE_DIR}/{self.dir}", True)
        self.video = video.make(
            created_by=user.make(),
            voice_model=voice_model.make(),
            gpt_answer=A_SCRIPT,
            dir_name=self.dir,
            settings=dict(narration=True),
        )

    def narrate(self):
        with patch("apps.videomanagement.utils.audio_utils.save") as spoken:
            spoken.side_effect = lambda syn, text, save_path, user=None: self.write(
                save_path
            )
            make_scenes_speech(self.video)

        return spoken

    def write(self, path):
        with open(f"{django_settings.BASE_DIR}/{path}", "wb") as f:
            f.write(b"RIFF")
        return path

    def test_narrates_every_line_on_the_first_run(self):
        self.assertEqual(self.narrate().call_count, 2)
        self.assertEqual(Scene.objects.filter(prompt=self.video.prompt).count(), 2)

    def test_does_not_narrate_or_duplicate_anything_on_a_second_run(self):
        self.narrate()

        self.assertEqual(self.narrate().call_count, 0)
        self.assertEqual(Scene.objects.filter(prompt=self.video.prompt).count(), 2)

    def test_narrates_only_the_line_whose_audio_never_landed(self):
        self.narrate()
        missing = Scene.objects.filter(prompt=self.video.prompt).first()
        os.remove(missing.file.path)

        self.assertEqual(self.narrate().call_count, 1)

    def test_a_line_that_will_not_synthesise_does_not_stop_the_others(self):
        first = True

        def flaky(syn, text, save_path, user=None):
            nonlocal first
            if first:
                first = False
                raise RuntimeError("429")
            return self.write(save_path)

        with patch("apps.videomanagement.utils.audio_utils.save", side_effect=flaky):
            make_scenes_speech(self.video)

        self.assertEqual(Scene.objects.filter(prompt=self.video.prompt).count(), 2)


class ResumeVisualsTests(TestCase):
    def setUp(self):
        self.dir = media_dir()
        os.makedirs(f"{django_settings.BASE_DIR}/{self.dir}", exist_ok=True)
        self.addCleanup(shutil.rmtree, f"{django_settings.BASE_DIR}/{self.dir}", True)
        self.video = video.make(
            created_by=user.make(),
            gpt_answer=A_SCRIPT,
            dir_name=self.dir,
            settings=dict(narration=True),
        )
        for sentence in A_SCRIPT["scenes"][0]["sentences"]:
            Scene.objects.create(prompt=self.video.prompt, text=sentence["sentence"])

    def illustrate(self):
        def produce(*args, **kwargs):
            path = os.path.join(self.dir, f"{slugify(kwargs['image'])}.png")
            with open(f"{django_settings.BASE_DIR}/{path}", "wb") as f:
                f.write(b"PNG")
            scene = Scene.objects.get(
                prompt=self.video.prompt, text=kwargs["text"].strip()
            )
            SceneImage.objects.create(scene=scene, file=path, prompt=kwargs["image"])
            return path

        with patch.object(
            scenes_utils, "create_image_scene", side_effect=produce
        ) as made:
            create_image_scenes(self.video, mode="WEB")

        return made

    def test_illustrates_every_sentence_on_the_first_run(self):
        self.assertEqual(self.illustrate().call_count, 2)

    def test_skips_a_sentence_that_already_has_its_visual(self):
        self.illustrate()

        self.assertEqual(self.illustrate().call_count, 0)

    def test_redoes_a_visual_whose_file_never_landed(self):
        self.illustrate()
        orphan = SceneImage.objects.first()
        os.remove(orphan.file.path)

        self.assertEqual(self.illustrate().call_count, 1)
