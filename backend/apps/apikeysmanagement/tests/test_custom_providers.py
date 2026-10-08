import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import voice_model
from apps.videomanagement.models import VoiceModel

from ..baker_recipes import user_custom_tts_provider
from ..models import ApiKeys, UserCustomTTSProvider


class CustomProviderApiTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.stranger = user.make()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.provider = user_custom_tts_provider.make(user=self.user)
        self.list_url = reverse("user-custom-tts-providers-list")
        self.detail_url = reverse(
            "user-custom-tts-providers-detail", args=[str(self.provider.pk)]
        )
        self.refresh_url = reverse(
            "user-custom-tts-providers-update-voices", args=[str(self.provider.pk)]
        )

    def test_lists_only_the_current_users_providers_and_masks_credentials(self):
        user_custom_tts_provider.make(user=self.stranger)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [str(self.provider.pk)])
        self.assertEqual(
            response.data[0]["api_key"], ApiKeys.mask(self.provider.api_key)
        )
        self.assertNotIn(self.provider.api_key, json.dumps(response.data))

    def test_creates_a_provider_for_the_authenticated_user_and_queues_its_voices(self):
        with patch("apps.videomanagement.tasks.update_user_voices.delay") as queue:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    self.list_url,
                    {
                        "name": "new_voice_service",
                        "endpoint_url": "https://example.com/speech",
                        "auth_type": "header",
                        "auth_header_name": "x-api-key",
                        "api_key": "new-secret-credential",
                        "voices_url": "https://example.com/voices",
                        "text_field_name": "input",
                        "voice_field_name": "speaker",
                        "user": self.stranger.pk,
                    },
                    format="json",
                )
        self.assertEqual(response.status_code, 201)
        created = UserCustomTTSProvider.objects.get(pk=response.data["id"])
        self.assertEqual(created.user, self.user)
        self.assertEqual(created.api_key, "new-secret-credential")
        self.assertEqual(created.text_field_name, "input")
        self.assertEqual(created.voice_field_name, "speaker")
        self.assertNotIn(created.api_key, json.dumps(response.data))
        queue.assert_called_once_with(self.user.pk, created.name)

    def test_patching_the_connection_preserves_the_saved_credential(self):
        response = self.client.patch(
            self.detail_url, {"endpoint_url": "https://example.com/new"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.endpoint_url, "https://example.com/new")
        self.assertEqual(self.provider.api_key, "secret-api-key")

    def test_can_replace_and_explicitly_clear_a_credential(self):
        for credential in ("replacement-secret", ""):
            with self.subTest(credential=credential):
                response = self.client.patch(
                    self.detail_url, {"api_key": credential}, format="json"
                )
                self.assertEqual(response.status_code, 200)
                self.provider.refresh_from_db()
                self.assertEqual(self.provider.api_key, credential)
                self.assertEqual(response.data["api_key"], ApiKeys.mask(credential))

    def test_rejects_custom_header_auth_without_a_header_name(self):
        response = self.client.patch(
            self.detail_url,
            {"auth_type": "header", "auth_header_name": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("auth_header_name", response.data)

    def test_partial_updates_can_reuse_a_saved_header_name(self):
        self.provider.auth_type = "header"
        self.provider.auth_header_name = "x-api-key"
        self.provider.save()
        response = self.client.patch(
            self.detail_url, {"api_key": "replacement"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_provider_names_are_unique_per_user(self):
        payload = {
            "name": self.provider.name,
            "endpoint_url": "https://example.com/speech",
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.client.force_authenticate(self.stranger)
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_rejects_invalid_connection_and_authentication_settings(self):
        for data, field in (
            ({"endpoint_url": "not-a-url"}, "endpoint_url"),
            ({"auth_type": "invalid"}, "auth_type"),
        ):
            with self.subTest(field=field):
                response = self.client.patch(self.detail_url, data, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)

    def test_refresh_queues_the_owners_provider_and_returns_accepted(self):
        with patch("apps.apikeysmanagement.views.update_user_voices.delay") as queue:
            response = self.client.post(self.refresh_url, {}, format="json")
        self.assertEqual(response.status_code, 202)
        queue.assert_called_once_with(self.user.pk, self.provider.name)

    def test_one_user_cannot_read_edit_delete_or_refresh_another_users_provider(self):
        self.client.force_authenticate(self.stranger)
        with patch("apps.apikeysmanagement.views.update_user_voices.delay") as queue:
            for method, url, data in (
                ("get", self.detail_url, None),
                ("patch", self.detail_url, {"api_key": "stolen"}),
                ("delete", self.detail_url, None),
                ("post", self.refresh_url, {}),
            ):
                with self.subTest(method=method):
                    response = getattr(self.client, method)(url, data, format="json")
                    self.assertEqual(response.status_code, 404)
            queue.assert_not_called()
        self.assertTrue(
            UserCustomTTSProvider.objects.filter(pk=self.provider.pk).exists()
        )

    def test_delete_removes_only_the_owners_imported_voices(self):
        mine = voice_model.make(
            created_by=self.user, provider=self.provider.name, type="CUSTOM_API"
        )
        theirs = voice_model.make(
            created_by=self.stranger, provider=self.provider.name, type="CUSTOM_API"
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(VoiceModel.objects.filter(pk=mine.pk).exists())
        self.assertTrue(VoiceModel.objects.filter(pk=theirs.pk).exists())

    def test_all_provider_actions_require_authentication(self):
        self.client.force_authenticate(None)
        for method, url, data in (
            ("get", self.list_url, None),
            ("post", self.list_url, {}),
            ("get", self.detail_url, None),
            ("patch", self.detail_url, {}),
            ("delete", self.detail_url, None),
            ("post", self.refresh_url, {}),
        ):
            with self.subTest(method=method, url=url):
                self.assertEqual(
                    getattr(self.client, method)(url, data, format="json").status_code,
                    401,
                )

    def test_builtin_provider_identifiers_cannot_be_used_for_custom_providers(self):
        for name in ("OPENAI", "ELEVENLABS", "SIXTYDB", "openai", "ElevenLabs"):
            with self.subTest(name=name):
                response = self.client.post(
                    self.list_url,
                    {"name": name, "endpoint_url": "https://example.com/speech"},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("name", response.data)

    def test_provider_names_are_immutable_so_imported_voices_keep_their_routing(self):
        response = self.client.patch(
            self.detail_url, {"name": "different-name"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.provider.refresh_from_db()
        self.assertNotEqual(self.provider.name, "different-name")

    def test_invalid_voices_urls_are_rejected_but_an_empty_url_is_optional(self):
        response = self.client.patch(
            self.detail_url, {"voices_url": "not a URL"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(self.detail_url, {"voices_url": ""}, format="json")
        self.assertEqual(response.status_code, 200)
