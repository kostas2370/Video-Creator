from datetime import timedelta

from django.conf import settings
from django.test import TestCase, override_settings
from model_bakery import baker
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

URL = "/api/login/"

PASSWORD = "a-very-good-password"


class RememberMeTests(TestCase):
    def setUp(self):
        self.user = baker.make_recipe("usermanagement.user")
        self.user.set_password(PASSWORD)
        self.user.save()
        self.client = APIClient()

    def login(self, **extra):
        return self.client.post(
            URL,
            {"username": self.user.username, "password": PASSWORD, **extra},
            format="json",
        )

    def test_signing_in_without_it_leaves_a_cookie_that_dies_with_the_browser(self):
        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["refresh_token"]["max-age"], "")
        self.assertEqual(response.cookies["access_token"]["max-age"], "")

    def test_signing_in_with_it_leaves_a_cookie_that_outlives_the_browser(self):
        response = self.login(remember_me=True)

        self.assertEqual(
            response.cookies["refresh_token"]["max-age"],
            int(settings.REMEMBER_ME_REFRESH_LIFETIME.total_seconds()),
        )

    def test_the_token_itself_lasts_as_long_as_the_cookie_claims(self):
        response = self.login(remember_me=True)

        token = RefreshToken(response.data["tokens"]["refresh"])
        lifetime = token.payload["exp"] - token.payload["iat"]

        self.assertEqual(
            lifetime, settings.REMEMBER_ME_REFRESH_LIFETIME.total_seconds()
        )

    def test_the_token_keeps_its_usual_life_without_it(self):
        response = self.login()

        token = RefreshToken(response.data["tokens"]["refresh"])
        lifetime = token.payload["exp"] - token.payload["iat"]

        self.assertEqual(
            lifetime, settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
        )

    def test_the_access_token_is_unaffected(self):
        for remember_me in (True, False):
            with self.subTest(remember_me=remember_me):
                tokens = self.user.get_tokens(remember_me=remember_me)

                access = RefreshToken(tokens["refresh"]).access_token
                self.assertEqual(
                    access.payload["exp"] - access.payload["iat"],
                    settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
                )

    @override_settings(REMEMBER_ME_REFRESH_LIFETIME=timedelta(days=90))
    def test_the_length_is_configurable(self):
        response = self.login(remember_me=True)

        self.assertEqual(
            response.cookies["refresh_token"]["max-age"],
            int(timedelta(days=90).total_seconds()),
        )

    def refresh(self, login_response):
        client = APIClient()
        client.cookies["refresh_token"] = login_response.cookies["refresh_token"].value
        return client.post("/api/token/refresh/")

    def test_refreshing_a_remembered_session_keeps_the_cookie_persistent(self):
        refreshed = self.refresh(self.login(remember_me=True))

        self.assertEqual(
            refreshed.cookies["access_token"]["max-age"],
            int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        )

    def test_refreshing_an_unremembered_session_does_not_make_it_persistent(self):
        refreshed = self.refresh(self.login())

        self.assertEqual(refreshed.cookies["access_token"]["max-age"], "")

    def test_it_is_not_echoed_back_in_the_response(self):
        response = self.login(remember_me=True)

        self.assertNotIn("remember_me", response.data)

    def test_a_string_from_a_form_post_still_counts(self):
        response = self.client.post(
            URL,
            {
                "username": self.user.username,
                "password": PASSWORD,
                "remember_me": "true",
            },
        )

        self.assertEqual(
            response.cookies["refresh_token"]["max-age"],
            int(settings.REMEMBER_ME_REFRESH_LIFETIME.total_seconds()),
        )
