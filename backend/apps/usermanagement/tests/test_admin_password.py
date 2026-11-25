from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from ..models import User


class AdminPasswordTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            "account-admin", "admin@example.test", "admin-secret-43"
        )
        self.client.force_login(self.admin)
        self.add_url = reverse("admin:usermanagement_user_add")
        self.password = "Local-test-secret-715"
        self.payload = {
            "username": "created-in-admin",
            "email": "created@example.test",
            "first_name": "Test",
            "last_name": "Account",
            "usable_password": "true",
            "password1": self.password,
            "password2": self.password,
        }

    def test_save_hashes_the_password_and_the_user_can_sign_in(self):
        response = self.client.post(self.add_url, self.payload)

        self.assertEqual(response.status_code, 302)
        account = User.objects.get(username=self.payload["username"])
        self.assertNotIn(self.password, account.password)
        self.assertTrue(account.check_password(self.password))
        self.assertNotContains(
            self.client.get(
                reverse("admin:usermanagement_user_change", args=[account.pk])
            ),
            self.password,
        )
        self.assertTrue(
            self.client.login(username=account.username, password=self.password)
        )

    def test_save_rejects_a_mismatched_confirmation(self):
        response = self.client.post(
            self.add_url, {**self.payload, "password2": "mismatch"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["adminform"].form.errors)
        self.assertFalse(
            User.objects.filter(username=self.payload["username"]).exists()
        )

    def test_staff_cannot_use_account_admin_with_delegated_permissions(self):
        staff = User.objects.create_user("staff", "staff@example.test", is_staff=True)
        staff.user_permissions.add(
            *Permission.objects.filter(content_type__app_label="usermanagement")
        )
        self.client.force_login(staff)

        self.assertEqual(self.client.post(self.add_url, self.payload).status_code, 403)
