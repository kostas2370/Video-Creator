from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.common.provider_errors import ProviderRequestError
from apps.usermanagement.baker_recipes import user

from ..baker_recipes import api_keys
from ..key_health import key_fingerprint, openai_request, openai_warning, save_warning
from ..models import ProviderKeyWarning


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
        self.assertNotIn(key_fingerprint(self.keys.openai_key), str(response.data))
        warning = ProviderKeyWarning.objects.get()
        self.assertNotIn(self.keys.openai_key, str(warning.__dict__))

    def test_replacing_or_removing_the_key_hides_the_old_warning(self):
        save_warning(self.keys.openai_key, "credentials")
        for key in ["sk-new-key", ""]:
            response = self.client.patch(self.url, {"openai_key": key}, format="json")
            self.assertIsNone(response.data["openai_warning"])

    def test_success_clears_the_warning_for_the_key_used(self):
        save_warning(self.keys.openai_key, "credentials")
        with openai_request(user=self.user):
            pass
        self.assertIsNone(self.client.get(self.url).data["openai_warning"])

    def test_transient_failures_do_not_mark_a_key_as_invalid(self):
        with self.assertRaises(ProviderRequestError):
            with openai_request(user=self.user):
                raise ProviderRequestError("rate_limit")
        self.assertIsNone(self.client.get(self.url).data["openai_warning"])

    def test_other_users_keys_do_not_inherit_the_warning(self):
        save_warning(self.keys.openai_key, "credentials")
        stranger = user.make(use_service_api_keys=False)
        api_keys.make(user=stranger, openai_key="sk-other-key")
        self.client.force_authenticate(stranger)
        self.assertIsNone(self.client.get(self.url).data["openai_warning"])

    @override_settings(OPEN_API_KEY="sk-shared-service-key")
    def test_service_key_warnings_follow_the_active_credential_mode(self):
        save_warning("sk-shared-service-key", "quota")
        self.assertIsNone(self.client.get(self.url).data["openai_warning"])
        response = self.client.patch(
            self.url, {"use_service_api_keys": True}, format="json"
        )
        self.assertEqual(response.data["openai_warning"]["code"], "quota")

    def test_old_in_flight_requests_cannot_change_a_replacement_keys_warning(self):
        old_key = self.keys.openai_key
        with self.assertRaises(ProviderRequestError):
            with openai_request(user=self.user):
                self.client.patch(
                    self.url, {"openai_key": "sk-replacement"}, format="json"
                )
                save_warning("sk-replacement", "access")
                raise ProviderRequestError("credentials")
        self.assertEqual(openai_warning(old_key)["code"], "credentials")
        self.assertEqual(
            self.client.get(self.url).data["openai_warning"]["code"], "access"
        )

    def test_an_earlier_success_does_not_clear_a_more_recent_rejection(self):
        with openai_request(user=self.user):
            save_warning(self.keys.openai_key, "credentials")
        self.assertEqual(
            self.client.get(self.url).data["openai_warning"]["code"], "credentials"
        )

    def test_missing_credentials_do_not_create_a_warning(self):
        save_warning(None, "credentials")
        self.assertIsNone(openai_warning(None))
        self.assertFalse(ProviderKeyWarning.objects.exists())

    def test_failed_status_storage_preserves_the_original_provider_error(self):
        from django.db import DatabaseError

        with patch(
            "apps.apikeysmanagement.key_health.ProviderKeyWarning.objects.update_or_create",
            side_effect=DatabaseError("unavailable"),
        ):
            with self.assertRaises(ProviderRequestError) as raised:
                with openai_request(user=self.user):
                    raise ProviderRequestError("credentials")
        self.assertEqual(raised.exception.code, "credentials")
