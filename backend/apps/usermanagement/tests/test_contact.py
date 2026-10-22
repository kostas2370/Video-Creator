from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", CONTACT_EMAIL="support@example.test")
class ContactTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.data = {"name": "Ada", "email": "ada@example.test", "message": "Can you help with my video?"}

    def submit(self, **changes):
        return self.client.post(reverse("contact"), {**self.data, **changes}, format="json")

    def test_public_form_delivers_to_support_with_reply_address(self):
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(mail.outbox[0].to, ["support@example.test"])
        self.assertEqual(mail.outbox[0].reply_to, ["ada@example.test"])
        self.assertIn(self.data["message"], mail.outbox[0].body)

    def test_rejects_invalid_and_empty_fields(self):
        for changes in ({"email": "bad"}, {"name": " "}, {"message": "short"}, {"message": "x" * 5001}):
            self.assertEqual(self.submit(**changes).status_code, 400)

    @patch("apps.usermanagement.contact.EmailMessage.send")
    def test_honeypot_does_not_send_mail(self, send):
        self.assertEqual(self.submit(website="spam.example").status_code, 200)
        send.assert_not_called()

    @patch("apps.usermanagement.contact.EmailMessage.send", side_effect=OSError("offline"))
    def test_delivery_failure_does_not_report_success(self, send):
        self.assertEqual(self.submit().status_code, 503)

    def test_rate_limits_public_submissions(self):
        for _ in range(5):
            self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(self.submit().status_code, 429)
