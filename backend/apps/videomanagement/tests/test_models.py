from django.test import TestCase
from apps.usermanagement.baker_recipes import user

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


class SelectAvatarTests(TestCase):
    def setUp(self):
        self.voice = voice_model.make()
        self.user = user.make()
        self.avatar = avatar.make(voice=self.voice, created_by=self.user)

    def test_returns_the_avatar_that_was_asked_for(self):
        self.assertEqual(Avatar.select_avatar(selected=self.avatar.id, user=self.user), self.avatar)

    def test_is_nothing_when_the_id_matches_no_avatar(self):
        self.assertIsNone(Avatar.select_avatar(selected=99999, user=self.user))

    def test_picks_at_random_when_none_was_named(self):
        self.assertEqual(Avatar.select_avatar(user=self.user), self.avatar)

    def test_picks_at_random_from_the_ones_that_share_a_voice(self):
        other_voice = voice_model.make()
        avatar.make(voice=other_voice, created_by=self.user)

        picked = Avatar.select_avatar(selected="random", voice_model=self.voice, user=self.user)

        self.assertEqual(picked, self.avatar)

    def test_never_selects_another_users_avatar(self):
        foreign = avatar.make(created_by=user.make(), voice=self.voice)
        self.assertIsNone(Avatar.select_avatar(selected=foreign.id, user=self.user))
        self.assertEqual(Avatar.select_avatar(user=self.user), self.avatar)

    def test_returns_none_without_an_owner_or_with_no_owned_avatars(self):
        self.assertIsNone(Avatar.select_avatar())
        self.assertIsNone(Avatar.select_avatar(user=user.make()))


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
