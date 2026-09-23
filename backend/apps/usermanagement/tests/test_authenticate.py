from datetime import timedelta

from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from ..authenticate import CustomAuthentication
from ..baker_recipes import user


class CustomAuthenticationTests(TestCase):
    def setUp(self):
        self.authentication = CustomAuthentication()
        self.user = user.make()
        self.access = str(RefreshToken.for_user(self.user).access_token)

    def request(self, token=None, **headers):
        request = APIRequestFactory().get("/", **headers)
        request.COOKIES = {"access_token": token} if token else {}
        return request

    def expired(self):
        token = RefreshToken.for_user(self.user).access_token
        token.set_exp(lifetime=timedelta(seconds=-1))
        return str(token)

    def test_signs_the_caller_in_from_the_access_cookie(self):
        authenticated, _ = self.authentication.authenticate(self.request(self.access))

        self.assertEqual(authenticated, self.user)

    def test_falls_back_to_the_authorization_header(self):
        request = self.request(HTTP_AUTHORIZATION=f"Bearer {self.access}")

        authenticated, _ = self.authentication.authenticate(request)

        self.assertEqual(authenticated, self.user)

    def test_prefers_the_cookie_over_the_header(self):
        stranger = user.make()
        request = self.request(
            self.access,
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(stranger).access_token}",
        )

        authenticated, _ = self.authentication.authenticate(request)

        self.assertEqual(authenticated, self.user)

    def test_leaves_a_request_with_no_credentials_anonymous(self):
        self.assertIsNone(self.authentication.authenticate(self.request()))

    def test_leaves_a_token_it_cannot_read_anonymous(self):
        self.assertIsNone(self.authentication.authenticate(self.request("not-a-token")))

    def test_leaves_a_refresh_token_in_the_access_cookie_anonymous(self):
        request = self.request(str(RefreshToken.for_user(self.user)))

        self.assertIsNone(self.authentication.authenticate(request))

    def test_a_stale_cookie_does_not_shut_out_a_live_header(self):
        request = self.request(
            self.expired(), HTTP_AUTHORIZATION=f"Bearer {self.access}"
        )

        authenticated, _ = self.authentication.authenticate(request)

        self.assertEqual(authenticated, self.user)

    def test_a_stale_cookie_on_its_own_leaves_the_caller_anonymous(self):
        self.assertIsNone(
            self.authentication.authenticate(self.request(self.expired()))
        )
