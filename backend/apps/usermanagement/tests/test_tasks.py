from django.core import mail
from django.test import TestCase, override_settings

from ..tasks import send_email


@override_settings(EMAIL_HOST_USER="noreply@example.test")
class SendEmailTests(TestCase):
    def test_sends_the_message_to_the_address_it_was_given(self):
        send_email("a subject", "ada@example.test", "a body")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "a subject")
        self.assertEqual(mail.outbox[0].body, "a body")
        self.assertEqual(mail.outbox[0].to, ["ada@example.test"])

    def test_sends_it_from_the_service_address(self):
        send_email("a subject", "ada@example.test", "a body")

        self.assertEqual(mail.outbox[0].from_email, "noreply@example.test")
