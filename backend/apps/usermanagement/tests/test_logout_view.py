from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from ..baker_recipes import user


class LogoutViewTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def logout(self, refresh=None):
        if refresh is not None:
            self.client.cookies["refresh_token"] = refresh
        return self.client.post(reverse("logout"))

    def test_blacklists_the_refresh_token_so_it_cannot_be_spent_again(self):
        refresh = RefreshToken.for_user(self.user)

        response = self.logout(str(refresh))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists()
        )

    def test_clears_the_cookies_it_signed_the_caller_in_with(self):
        response = self.logout(str(RefreshToken.for_user(self.user)))

        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")

    def test_refuses_a_request_that_carries_no_refresh_token(self):
        response = self.logout()

        self.assertEqual(response.status_code, 400)
        self.assertFalse(BlacklistedToken.objects.exists())

    def test_refuses_a_refresh_token_it_cannot_read(self):
        self.assertEqual(self.logout("not-a-token").status_code, 400)

    def test_refuses_a_token_that_was_already_blacklisted(self):
        refresh = RefreshToken.for_user(self.user)
        self.logout(str(refresh))

        self.assertEqual(self.logout(str(refresh)).status_code, 400)

    def test_still_works_once_the_access_token_has_expired(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.force_authenticate(None)

        response = self.logout(str(refresh))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists()
        )

    def test_refuses_an_unauthenticated_caller_with_no_refresh_token(self):
        self.client.force_authenticate(None)

        self.assertEqual(self.logout().status_code, 400)
