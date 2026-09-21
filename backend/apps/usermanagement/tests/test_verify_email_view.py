from unittest.mock import patch

import jwt
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from ..baker_recipes import unverified_user, user


def token_for(account):
    return str(RefreshToken.for_user(account).access_token)


class VerifyEmailViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = unverified_user.make()

    def verify(self, token=None):
        query = f"?token={token}" if token is not None else ""
        return self.client.get(f"{reverse('email-verify')}{query}")

    def test_activates_the_account_the_token_belongs_to(self):
        response = self.verify(token_for(self.user))

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

    def test_refuses_an_account_that_is_already_verified(self):
        response = self.verify(token_for(user.make()))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "User is already verified")

    def test_refuses_a_token_it_cannot_read(self):
        response = self.verify("not-a-token")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Invalid Token")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)

    def test_refuses_a_request_with_no_token_at_all(self):
        response = self.verify()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Invalid Token")

    def test_refuses_a_token_that_has_run_out(self):
        with patch.object(jwt, "decode", side_effect=jwt.ExpiredSignatureError):
            response = self.verify(token_for(self.user))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Token Expired")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)

    def test_is_open_to_a_caller_who_is_not_signed_in(self):
        self.assertEqual(self.verify(token_for(self.user)).status_code, 200)
