from django.test import TestCase

from ..baker_recipes import (
    avatar,
    background,
    music,
    template_prompt,
    video,
    voice_model,
)
from ..models import Avatar, Background, UserPrompt, Video, VoiceModel


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


class SelectVoiceTests(TestCase):
    def test_picks_one_of_the_voices_on_file(self):
        voices = voice_model.make(_quantity=3)

        self.assertIn(VoiceModel.select_voice(), voices)


class SelectAvatarTests(TestCase):
    def setUp(self):
        self.voice = voice_model.make()
        self.avatar = avatar.make(voice=self.voice)

    def test_returns_the_avatar_that_was_asked_for(self):
        self.assertEqual(Avatar.select_avatar(selected=self.avatar.id), self.avatar)

    def test_is_nothing_when_the_id_matches_no_avatar(self):
        self.assertIsNone(Avatar.select_avatar(selected=99999))

    def test_picks_at_random_when_none_was_named(self):
        self.assertEqual(Avatar.select_avatar(), self.avatar)

    def test_picks_at_random_from_the_ones_that_share_a_voice(self):
        other_voice = voice_model.make()
        avatar.make(voice=other_voice)

        picked = Avatar.select_avatar(selected="random", voice_model=self.voice)

        self.assertEqual(picked, self.avatar)


class SelectBackgroundTests(TestCase):
    def test_picks_one_of_the_backgrounds_on_file(self):
        backgrounds = background.make(_quantity=3)

        self.assertIn(Background.select_background(), backgrounds)

    def test_is_nothing_when_there_is_no_background_to_pick(self):
        self.assertIsNone(Background.select_background())


class StringRepresentationTests(TestCase):
    """Names the admin lists rows by."""

    def test_models_are_named_by_the_field_a_person_would_recognise(self):
        for recipe, attribute in (
            (template_prompt, "title"),
            (music, "name"),
            (voice_model, "name"),
            (avatar, "name"),
            (background, "name"),
            (video, "title"),
        ):
            instance = recipe.prepare()
            with self.subTest(model=type(instance).__name__):
                self.assertEqual(str(instance), getattr(instance, attribute))
