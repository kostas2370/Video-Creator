from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from ..models import AccessRequest, User
from ..services import approve_access_request


@override_settings(SIGNUP_ALLOWED_EMAILS=(), USER_LIMIT=10)
class AccessRequestTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient()
        self.payload = {
            "name": "Ada",
            "email": "Ada@Example.test",
            "message": "I want to create educational videos.",
        }
        self.admin = User.objects.create_superuser(
            "operator", "operator@example.test", "Secret123!"
        )

    def submit(self, **overrides):
        return self.client.post(
            reverse("access-request"), {**self.payload, **overrides}, format="json"
        )

    def register(self, email="ada@example.test"):
        return self.client.post(
            reverse("register"),
            {
                "username": "ada",
                "email": email,
                "password": "StrongPassword1!",
            },
            format="json",
        )

    def test_request_is_public_and_does_not_create_an_account_or_send_email(self):
        response = self.submit(status="approved", reviewed_by=str(self.admin.pk))
        self.assertEqual(response.status_code, 202)
        entry = AccessRequest.objects.get()
        self.assertEqual(entry.email, "ada@example.test")
        self.assertEqual(entry.status, AccessRequest.Status.PENDING)
        self.assertIsNone(entry.reviewed_by)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(mail.outbox, [])

    def test_duplicates_return_the_same_response_and_preserve_the_review(self):
        self.submit()
        entry = AccessRequest.objects.get()
        entry.status = AccessRequest.Status.REJECTED
        entry.save()
        response = self.submit(email="ada@example.test", name="Changed")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(AccessRequest.objects.count(), 1)
        entry.refresh_from_db()
        self.assertEqual(entry.status, AccessRequest.Status.REJECTED)
        self.assertEqual(entry.name, "Ada")

    def test_honeypot_does_not_store_a_request(self):
        self.assertEqual(self.submit(website="spam.test").status_code, 202)
        self.assertFalse(AccessRequest.objects.exists())

    def test_validates_email_message_and_lengths(self):
        for data in (
            {"email": "invalid"},
            {"message": "short"},
            {"message": "x" * 2001},
            {"name": "x" * 101},
        ):
            self.assertEqual(self.submit(**data).status_code, 400)
        self.assertFalse(AccessRequest.objects.exists())

    def test_throttles_requests_even_when_validation_fails(self):
        for _ in range(5):
            self.assertEqual(self.submit(email="invalid").status_code, 400)
        self.assertEqual(self.submit().status_code, 429)

    def test_pending_and_rejected_requests_cannot_register(self):
        self.submit()
        self.assertEqual(self.register().status_code, 400)
        AccessRequest.objects.update(status=AccessRequest.Status.REJECTED)
        self.assertEqual(self.register().status_code, 400)

    @override_settings(FRONTEND_URL="https://viddie.example")
    def test_approval_invites_the_same_email_and_registration_still_needs_verification(
        self,
    ):
        self.submit()
        entry = AccessRequest.objects.get()
        self.assertTrue(approve_access_request(entry.pk, self.admin))
        entry.refresh_from_db()
        self.assertEqual(entry.reviewed_by, self.admin)
        self.assertIsNotNone(entry.reviewed_at)
        self.assertEqual(mail.outbox[0].to, ["ada@example.test"])
        self.assertIn("https://viddie.example/register/", mail.outbox[0].body)
        self.assertEqual(self.register("Ada@Example.test").status_code, 201)
        self.assertFalse(User.objects.get(username="ada").is_verified)
        self.assertEqual(self.register("other@example.test").status_code, 400)

    def test_approval_is_idempotent(self):
        self.submit()
        entry = AccessRequest.objects.get()
        self.assertTrue(approve_access_request(entry.pk, self.admin))
        self.assertFalse(approve_access_request(entry.pk, self.admin))
        self.assertEqual(len(mail.outbox), 1)

    @patch(
        "apps.usermanagement.services.send_mail",
        side_effect=RuntimeError("SMTP unavailable"),
    )
    def test_delivery_failure_leaves_the_request_pending(self, send):
        self.submit()
        entry = AccessRequest.objects.get()
        with self.assertRaises(RuntimeError):
            approve_access_request(entry.pk, self.admin)
        entry.refresh_from_db()
        self.assertEqual(entry.status, AccessRequest.Status.PENDING)
        self.assertIsNone(entry.reviewed_at)
        self.assertEqual(self.register().status_code, 400)

    @override_settings(SIGNUP_ALLOWED_EMAILS=None)
    def test_open_registration_is_unchanged(self):
        self.assertEqual(self.register().status_code, 201)

    def test_existing_email_allowlist_still_allows_registration(self):
        with override_settings(SIGNUP_ALLOWED_EMAILS=("ada@example.test",)):
            self.assertEqual(self.register().status_code, 201)

    def test_superuser_can_approve_requests_from_admin(self):
        self.submit()
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:usermanagement_accessrequest_changelist"),
            {
                "action": "approve_requests",
                "_selected_action": str(AccessRequest.objects.get().pk),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            AccessRequest.objects.get().status, AccessRequest.Status.APPROVED
        )

    def test_rejection_records_the_reviewer_without_inviting(self):
        self.submit()
        self.client.force_login(self.admin)
        self.client.post(
            reverse("admin:usermanagement_accessrequest_changelist"),
            {
                "action": "reject_requests",
                "_selected_action": str(AccessRequest.objects.get().pk),
            },
        )
        entry = AccessRequest.objects.get()
        self.assertEqual(entry.status, AccessRequest.Status.REJECTED)
        self.assertEqual(entry.reviewed_by, self.admin)
        self.assertEqual(mail.outbox, [])

    def test_staff_cannot_review_requests_even_with_delegated_permissions(self):
        self.submit()
        staff = User.objects.create_user("staff", "staff@example.test", is_staff=True)
        staff.user_permissions.add(
            *Permission.objects.filter(content_type__model="accessrequest")
        )
        self.client.force_login(staff)
        self.assertEqual(
            self.client.get(
                reverse("admin:usermanagement_accessrequest_changelist")
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("admin:usermanagement_accessrequest_changelist"),
                {
                    "action": "approve_requests",
                    "_selected_action": str(AccessRequest.objects.get().pk),
                },
            ).status_code,
            403,
        )
        self.assertEqual(
            AccessRequest.objects.get().status, AccessRequest.Status.PENDING
        )

    def test_public_endpoint_never_lists_requests(self):
        self.submit()
        self.assertEqual(self.client.get(reverse("access-request")).status_code, 405)
