from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django_rest_passwordreset.models import ResetPasswordToken
from rest_framework.test import APIClient

from ..baker_recipes import user


@override_settings(FRONTEND_URL="https://app.test", PASSWORD_RESET_PATH="/reset")
class PasswordResetTokenCreatedTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.client = APIClient()

        notify = patch("apps.usermanagement.signals.send_email.delay")
        self.send_email = notify.start()
        self.addCleanup(notify.stop)

    def request_reset(self, email=None):
        return self.client.post(
            reverse("password_reset:reset-password-request"),
            {"email": email or self.user.email},
        )

    def test_mails_a_reset_link_that_points_at_the_frontend(self):
        response = self.request_reset()

        self.assertEqual(response.status_code, 200)
        token = ResetPasswordToken.objects.get(user=self.user)
        self.send_email.assert_called_once()
        self.assertEqual(self.send_email.call_args.kwargs["email"], self.user.email)
        self.assertIn(
            f"https://app.test/reset?token={token.key}",
            self.send_email.call_args.kwargs["text"],
        )

    def test_names_the_mail_so_the_owner_knows_what_it_is(self):
        self.request_reset()

        self.assertEqual(
            self.send_email.call_args.kwargs["name"],
            "Password Reset for Your Account",
        )

    def test_mails_nothing_for_an_address_no_account_holds(self):
        self.request_reset(email="nobody@example.test")

        self.send_email.assert_not_called()
