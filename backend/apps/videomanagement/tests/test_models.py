from unittest.mock import patch

from django.test import TestCase
from model_bakery import baker

from ..models import Avatar, Background, VoiceModel


class SelectVoiceTests(TestCase):
    def test_picks_one_of_the_voices_on_file(self):
        voices = baker.make_recipe("videomanagement.voice_model", _quantity=3)

        self.assertIn(VoiceModel.select_voice(), voices)


class SelectAvatarTests(TestCase):
    def setUp(self):
        self.voice = baker.make_recipe("videomanagement.voice_model")
        self.avatar = baker.make_recipe("videomanagement.avatar", voice=self.voice)

    def test_returns_the_avatar_that_was_asked_for(self):
        self.assertEqual(Avatar.select_avatar(selected=self.avatar.id), self.avatar)

    def test_is_nothing_when_the_id_matches_no_avatar(self):
        self.assertIsNone(Avatar.select_avatar(selected=99999))

    def test_picks_at_random_when_none_was_named(self):
        self.assertEqual(Avatar.select_avatar(), self.avatar)

    def test_picks_at_random_from_the_ones_that_share_a_voice(self):
        other_voice = baker.make_recipe("videomanagement.voice_model")
        baker.make_recipe("videomanagement.avatar", voice=other_voice)

        picked = Avatar.select_avatar(selected="random", voice_model=self.voice)

        self.assertEqual(picked, self.avatar)


class SelectBackgroundTests(TestCase):
    def test_picks_from_the_category_that_was_asked_for(self):
        wanted = baker.make_recipe("videomanagement.background", category="GAMING")
        baker.make_recipe("videomanagement.background", category="STORY")

        self.assertEqual(Background.select_background("GAMING"), wanted)

    def test_picks_from_all_of_them_when_no_category_was_asked_for(self):
        backgrounds = baker.make_recipe("videomanagement.background", _quantity=3)

        self.assertIn(Background.select_background(), backgrounds)


class StringRepresentationTests(TestCase):
    """Names the admin lists rows by."""

    def test_models_are_named_by_the_field_a_person_would_recognise(self):
        for recipe, attribute in (
            ("videomanagement.template_prompt", "title"),
            ("videomanagement.music", "name"),
            ("videomanagement.voice_model", "name"),
            ("videomanagement.avatar", "name"),
            ("videomanagement.background", "name"),
            ("videomanagement.video", "title"),
        ):
            with self.subTest(recipe=recipe):
                instance = baker.prepare_recipe(recipe)
                self.assertEqual(str(instance), getattr(instance, attribute))


class UserTests(TestCase):
    def test_issues_a_usable_token_pair(self):
        user = baker.make_recipe("usermanagement.user")

        tokens = user.get_tokens()

        self.assertIn("access", tokens)
        self.assertIn("refresh", tokens)

    def test_reports_both_halves_of_the_name(self):
        user = baker.prepare_recipe(
            "usermanagement.user", first_name="Ada", last_name="Lovelace"
        )

        self.assertEqual(user.get_full_name(), "Ada Lovelace")
        self.assertEqual(user.get_short_name(), "Ada")

    def test_normalises_the_email_domain_on_clean(self):
        user = baker.prepare_recipe("usermanagement.user", email="Ada@EXAMPLE.TEST")

        user.clean()

        self.assertEqual(user.email, "Ada@example.test")

    def test_sends_mail_to_the_users_own_address(self):
        user = baker.make_recipe("usermanagement.user", email="ada@example.test")

        with patch("apps.usermanagement.models.send_mail") as send:
            user.email_user("subject", "body")

        self.assertEqual(send.call_args.args[3], ["ada@example.test"])


class LoginTests(TestCase):
    def test_reads_the_client_ip_from_the_forwarding_header_when_there_is_one(self):
        from apps.usermanagement.models import Login

        request = type("Request", (), {})()
        request.META = {"HTTP_X_FORWARDED_FOR": "1.2.3.4, 5.6.7.8"}

        self.assertEqual(Login.get_user_ip(request), "1.2.3.4")

    def test_falls_back_to_the_socket_address(self):
        from apps.usermanagement.models import Login

        request = type("Request", (), {})()
        request.META = {"REMOTE_ADDR": "9.9.9.9"}

        self.assertEqual(Login.get_user_ip(request), "9.9.9.9")
