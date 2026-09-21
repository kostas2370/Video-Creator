from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from ..baker_recipes import user


class CookieTokenRefreshViewTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.client = APIClient()

    def refresh(self, token=None):
        if token is not None:
            self.client.cookies["refresh_token"] = token
        return self.client.post(reverse("token_refresh"))

    def test_hands_back_a_fresh_access_token_for_a_good_cookie(self):
        response = self.refresh(str(RefreshToken.for_user(self.user)))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AccessToken(response.data["access"])["user_id"], self.user.id)

    def test_leaves_the_new_access_token_in_a_cookie(self):
        response = self.refresh(str(RefreshToken.for_user(self.user)))

        self.assertEqual(
            response.cookies["access_token"].value, response.data["access"]
        )

    def test_tells_a_caller_with_no_cookie_to_set_one(self):
        response = self.refresh()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["Message"], "You need to set refresh token")

    def test_refuses_a_cookie_it_cannot_read(self):
        response = self.refresh("not-a-token")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["Message"], "This token has expired")

    def test_refuses_a_token_that_signing_out_blacklisted(self):
        refresh = RefreshToken.for_user(self.user)
        refresh.blacklist()

        self.assertEqual(self.refresh(str(refresh)).status_code, 400)

    def test_echoes_the_csrf_cookie_back_as_a_header(self):
        self.client.cookies["csrftoken"] = "a-csrf-token"

        response = self.refresh(str(RefreshToken.for_user(self.user)))

        self.assertEqual(response["X-CSRFToken"], "a-csrf-token")
