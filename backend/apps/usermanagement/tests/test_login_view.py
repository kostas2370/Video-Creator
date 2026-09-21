from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from ..baker_recipes import unverified_user, user
from ..models import Login

PASSWORD = "a-Very-Good-1"


class LoginViewTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.user.set_password(PASSWORD)
        self.user.save()
        self.client = APIClient()

        notify = patch("apps.usermanagement.views.send_email.delay")
        self.send_email = notify.start()
        self.addCleanup(notify.stop)

    def login(self, account=None, password=PASSWORD, **extra):
        return self.client.post(
            reverse("login"),
            {"username": (account or self.user).username, "password": password},
            **extra,
        )

    def test_signs_a_verified_account_in_and_hands_back_its_tokens(self):
        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            AccessToken(response.data["tokens"]["access"])["user_id"], self.user.id
        )

    def test_leaves_the_tokens_in_cookies_the_browser_sends_back(self):
        response = self.login()

        self.assertEqual(
            response.cookies["access_token"].value, response.data["tokens"]["access"]
        )
        self.assertEqual(
            response.cookies["refresh_token"].value, response.data["tokens"]["refresh"]
        )
        self.assertTrue(response.cookies["access_token"]["httponly"])

    def test_hands_out_a_csrf_token_for_the_session(self):
        self.assertTrue(self.login()["X-CSRFToken"])

    def test_records_the_address_the_sign_in_came_from(self):
        self.login(REMOTE_ADDR="9.9.9.9")

        self.assertTrue(Login.objects.filter(user=self.user, ip="9.9.9.9").exists())

    def test_reads_the_address_from_the_forwarding_header_when_there_is_one(self):
        self.login(HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8", REMOTE_ADDR="9.9.9.9")

        self.assertTrue(Login.objects.filter(user=self.user, ip="1.2.3.4").exists())

    def test_warns_the_owner_the_first_time_an_address_is_seen(self):
        self.login(REMOTE_ADDR="9.9.9.9")

        self.send_email.assert_called_once()
        self.assertEqual(self.send_email.call_args.args[1], self.user.email)
        self.assertIn("9.9.9.9", self.send_email.call_args.args[2])

    def test_stays_quiet_for_an_address_it_has_already_seen(self):
        self.login(REMOTE_ADDR="9.9.9.9")
        self.send_email.reset_mock()

        self.login(REMOTE_ADDR="9.9.9.9")

        self.send_email.assert_not_called()
        self.assertEqual(Login.objects.filter(user=self.user).count(), 1)

    def test_counts_every_sign_in_from_the_same_address(self):
        for _ in range(3):
            self.login(REMOTE_ADDR="9.9.9.9")

        self.assertEqual(Login.objects.get(user=self.user, ip="9.9.9.9").count, 3)

    def test_warns_again_when_the_next_sign_in_comes_from_somewhere_else(self):
        self.login(REMOTE_ADDR="9.9.9.9")
        self.send_email.reset_mock()

        self.login(REMOTE_ADDR="8.8.8.8")

        self.send_email.assert_called_once()
        self.assertEqual(Login.objects.filter(user=self.user).count(), 2)

    def test_turns_away_the_wrong_password(self):
        response = self.login(password="not-the-password")

        self.assertEqual(response.status_code, 401)
        self.assertFalse(Login.objects.exists())

    def test_turns_away_a_username_no_account_holds(self):
        response = self.client.post(
            reverse("login"), {"username": "nobody", "password": PASSWORD}
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(Login.objects.exists())

    def test_turns_away_a_request_with_no_username_at_all(self):
        response = self.client.post(reverse("login"), {"password": PASSWORD})

        self.assertEqual(response.status_code, 400)

    def test_turns_away_an_account_that_was_never_verified(self):
        pending = unverified_user.make()
        pending.set_password(PASSWORD)
        pending.save()

        response = self.login(account=pending)

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("access_token", response.cookies)
