from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.common.provider_errors import ProviderRequestError
from apps.usermanagement.baker_recipes import user

from ..baker_recipes import api_keys
from ..key_health import openai_request, save_warning
from ..models import ApiKeys


class KeyHealthTests(TestCase):
    def setUp(self):
        self.user = user.make(use_service_api_keys=False)
        self.keys = api_keys.make(user=self.user, openai_key="sk-private-rejected-key")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse("api-keys")

    def test_rejected_requests_leave_a_warning_in_settings_after_reload(self):
        with self.assertRaises(ProviderRequestError):
            with openai_request(user=self.user) as key:
                self.assertEqual(key, self.keys.openai_key)
                raise ProviderRequestError("credentials")
        response = self.client.get(self.url)
        self.assertEqual(response.data["openai_warning"]["code"], "credentials")
        self.assertNotIn(self.keys.openai_key, str(response.data))
        self.keys.refresh_from_db()
        self.assertEqual(self.keys.openai_warning, "credentials")

    def test_replacing_or_removing_the_key_clears_the_warning(self):
        for key in ["sk-new-key", ""]:
            save_warning(self.user, "credentials")
            response = self.client.patch(self.url, {"openai_key": key}, format="json")
            self.assertIsNone(response.data["openai_warning"])

    def test_success_clears_the_warning(self):
        save_warning(self.user, "credentials")
        with openai_request(user=self.user):
            pass
        self.assertIsNone(self.client.get(self.url).data["openai_warning"])

    def test_transient_failures_do_not_mark_a_key_as_invalid(self):
        with self.assertRaises(ProviderRequestError):
            with openai_request(user=self.user):
                raise ProviderRequestError("rate_limit")
        self.assertIsNone(self.client.get(self.url).data["openai_warning"])

    def test_other_users_do_not_inherit_the_warning(self):
        save_warning(self.user, "credentials")
        self.client.force_authenticate(user.make())
        self.assertIsNone(self.client.get(self.url).data["openai_warning"])

    @override_settings(OPEN_API_KEY="sk-shared-service-key")
    def test_switching_credential_mode_clears_the_old_warning(self):
        save_warning(self.user, "credentials")
        response = self.client.patch(
            self.url, {"use_service_api_keys": True}, format="json"
        )
        self.assertIsNone(response.data["openai_warning"])
        with self.assertRaises(ProviderRequestError):
            with openai_request(user=ApiKeys.objects.get(user=self.user).user) as key:
                self.assertEqual(key, "sk-shared-service-key")
                raise ProviderRequestError("quota")
        self.assertEqual(
            self.client.get(self.url).data["openai_warning"]["code"], "quota"
        )

    def test_service_users_without_a_key_record_can_save_a_warning(self):
        actor = user.make(use_service_api_keys=True)
        save_warning(actor, "credentials")
        self.assertEqual(ApiKeys.objects.get(user=actor).openai_warning, "credentials")

    def test_warnings_cannot_be_changed_through_the_api(self):
        save_warning(self.user, "credentials")
        response = self.client.patch(
            self.url, {"openai_warning": "quota"}, format="json"
        )
        self.assertEqual(response.data["openai_warning"]["code"], "credentials")

    def test_failed_warning_storage_preserves_the_provider_error(self):
        with patch(
            "apps.apikeysmanagement.key_health.ApiKeys.objects.get_or_create",
            side_effect=DatabaseError("unavailable"),
        ):
            with self.assertRaises(ProviderRequestError) as raised:
                with openai_request(user=self.user):
                    raise ProviderRequestError("credentials")
        self.assertEqual(raised.exception.code, "credentials")
