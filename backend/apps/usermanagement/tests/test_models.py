from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from ..baker_recipes import login, user
from ..models import Login, User


class UserTests(TestCase):
    def test_is_named_by_the_username_the_admin_lists_it_by(self):
        ada = user.prepare(username="ada")

        self.assertEqual(str(ada), "ada")

    def test_reports_both_halves_of_the_name(self):
        ada = user.prepare(first_name="Ada", last_name="Lovelace")

        self.assertEqual(ada.get_full_name(), "Ada Lovelace")
        self.assertEqual(ada.get_short_name(), "Ada")

    def test_normalises_the_email_domain_on_clean(self):
        ada = user.prepare(email="Ada@EXAMPLE.TEST")

        ada.clean()

        self.assertEqual(ada.email, "Ada@example.test")

    def test_sends_mail_to_the_users_own_address(self):
        ada = user.make(email="ada@example.test")

        with patch("apps.usermanagement.models.send_mail") as send:
            ada.email_user("subject", "body")

        self.assertEqual(send.call_args.args[3], ["ada@example.test"])

    def test_starts_unverified_with_no_allowance_to_spend(self):
        fresh = User(username="fresh", email="fresh@example.test")

        self.assertFalse(fresh.is_verified)
        self.assertEqual(fresh.generation_limit_for_ai, 0)
        self.assertEqual(fresh.generation_limit_for_twitch, 0)
        self.assertTrue(fresh.use_service_api_keys)

    def test_two_accounts_can_never_share_an_email(self):
        user.make(email="ada@example.test")

        with self.assertRaises(Exception):
            user.make(email="ada@example.test")


class GetTokensTests(TestCase):
    def setUp(self):
        self.user = user.make()

    def test_issues_a_usable_token_pair(self):
        tokens = self.user.get_tokens()

        self.assertEqual(AccessToken(tokens["access"])["user_id"], self.user.id)
        self.assertEqual(RefreshToken(tokens["refresh"])["user_id"], self.user.id)

    def test_a_remembered_pair_carries_the_flag_the_refresh_view_reads(self):
        tokens = self.user.get_tokens(remember_me=True)

        self.assertTrue(RefreshToken(tokens["refresh"])["remember_me"])

    def test_an_ordinary_pair_carries_no_such_flag(self):
        tokens = self.user.get_tokens()

        self.assertNotIn("remember_me", RefreshToken(tokens["refresh"]).payload)

    def test_a_remembered_refresh_token_lives_as_long_as_the_setting_says(self):
        token = RefreshToken(self.user.get_tokens(remember_me=True)["refresh"])

        lifetime = token.payload["exp"] - token.payload["iat"]

        self.assertEqual(
            lifetime, settings.REMEMBER_ME_REFRESH_LIFETIME.total_seconds()
        )

    def test_the_row_that_guards_a_remembered_token_outlives_the_token(self):
        token = RefreshToken(self.user.get_tokens(remember_me=True)["refresh"])

        outstanding = OutstandingToken.objects.get(jti=token["jti"])

        self.assertEqual(outstanding.expires_at.timestamp(), token["exp"])

    def test_the_access_token_keeps_its_own_lifetime_either_way(self):
        for remember_me in (False, True):
            with self.subTest(remember_me=remember_me):
                token = AccessToken(
                    self.user.get_tokens(remember_me=remember_me)["access"]
                )

                self.assertEqual(
                    token.payload["exp"] - token.payload["iat"],
                    settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
                )


class LoginTests(TestCase):
    def request_with(self, **meta):
        request = type("Request", (), {})()
        request.META = meta
        return request

    @override_settings(TRUSTED_PROXY_HOPS=0)
    def test_ignores_a_forwarding_header_no_proxy_of_ours_wrote(self):
        request = self.request_with(
            HTTP_X_FORWARDED_FOR="1.2.3.4", REMOTE_ADDR="9.9.9.9"
        )

        self.assertEqual(Login.get_user_ip(request), "9.9.9.9")

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_reads_the_address_our_own_proxy_appended(self):
        request = self.request_with(
            HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8", REMOTE_ADDR="10.0.0.1"
        )

        self.assertEqual(Login.get_user_ip(request), "5.6.7.8")

    def test_falls_back_to_the_socket_address(self):
        request = self.request_with(REMOTE_ADDR="9.9.9.9")

        self.assertEqual(Login.get_user_ip(request), "9.9.9.9")

    def test_is_nothing_when_the_request_carries_no_address_at_all(self):
        self.assertIsNone(Login.get_user_ip(self.request_with()))

    def test_names_the_row_by_its_user_and_address(self):
        row = login.make(user=user.make(username="ada"), ip="1.2.3.4")

        self.assertIn("ada (1.2.3.4) at", str(row))

    def test_counts_nothing_until_a_sign_in_is_recorded(self):
        self.assertEqual(login.make().count, 0)

    def test_goes_away_with_the_user_it_belongs_to(self):
        row = login.make()

        row.user.delete()

        self.assertFalse(Login.objects.filter(pk=row.pk).exists())
