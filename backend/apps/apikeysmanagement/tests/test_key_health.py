from unittest.mock import MagicMock, Mock, patch

import requests
from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.common.provider_errors import ProviderRequestError
from apps.usermanagement.baker_recipes import user

from ..baker_recipes import api_keys
from ..provider_requests import key_request, openai_request, provider_request, save_warning
from ..models import ApiKeys, Provider


class KeyHealthTests(TestCase):
    def setUp(self):
        self.user = user.make(use_service_api_keys=False)
        self.keys = api_keys.make(user=self.user, openai_key="sk-private-rejected-key")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse("api-keys")

    def response(self, provider, status):
        with patch(
            "apps.apikeysmanagement.provider_requests.requests.request",
            return_value=Mock(status_code=status),
        ):
            return provider_request(
                "POST", "https://provider.invalid/", user=self.user, provider=provider
            )

    def test_401_responses_set_a_separate_warning_for_each_builtin_key(self):
        providers = set(ApiKeys.FIELDS) - {Provider.GOOGLE_SEARCH_ENGINE_ID}
        for provider in providers:
            self.response(provider, 401)
        response = self.client.get(self.url)
        self.assertEqual(response.data["key_warnings"], dict.fromkeys(providers, True))
        self.assertNotIn(self.keys.openai_key, str(response.data))

    def test_sdk_and_wrapped_http_401_errors_save_warnings(self):
        error = requests.HTTPError(response=Mock(status_code=401))
        with self.assertRaises(requests.HTTPError):
            with key_request(self.user, Provider.ANTHROPIC):
                raise error
        with self.assertRaises(ProviderRequestError):
            with openai_request(self.user):
                raise ProviderRequestError("credentials")
        self.assertEqual(
            self.client.get(self.url).data["key_warnings"],
            {"ANTHROPIC": True, "OPENAI": True},
        )

    def test_other_statuses_do_not_mark_keys_as_revoked(self):
        for status in [400, 403, 429, 500]:
            self.response(Provider.OPENAI, status)
            with self.assertRaises(requests.HTTPError):
                with key_request(self.user, Provider.GEMINI):
                    raise requests.HTTPError(response=Mock(status_code=status))
        self.assertEqual(self.client.get(self.url).data["key_warnings"], {})

    def test_success_clears_only_the_matching_providers_warning(self):
        save_warning(self.user, Provider.OPENAI, True)
        save_warning(self.user, Provider.GEMINI, True)
        with openai_request(self.user):
            pass
        self.assertEqual(
            self.client.get(self.url).data["key_warnings"], {"GEMINI": True}
        )
        self.response(Provider.GEMINI, 200)
        self.assertEqual(self.client.get(self.url).data["key_warnings"], {})

    def test_replacing_a_key_clears_only_that_providers_warning(self):
        save_warning(self.user, Provider.OPENAI, True)
        save_warning(self.user, Provider.GEMINI, True)
        response = self.client.patch(
            self.url, {"openai_key": "sk-replacement"}, format="json"
        )
        self.assertEqual(response.data["key_warnings"], {"GEMINI": True})

    def test_resaving_the_same_key_preserves_its_warning(self):
        save_warning(self.user, Provider.OPENAI, True)
        response = self.client.patch(
            self.url, {"openai_key": self.keys.openai_key}, format="json"
        )
        self.assertEqual(response.data["key_warnings"], {"OPENAI": True})

    def test_switching_credential_mode_clears_the_previous_modes_warnings(self):
        save_warning(self.user, Provider.OPENAI, True)
        response = self.client.patch(
            self.url, {"use_service_api_keys": True}, format="json"
        )
        self.assertEqual(response.data["key_warnings"], {})

    def test_other_users_do_not_inherit_the_warning(self):
        save_warning(self.user, Provider.OPENAI, True)
        self.client.force_authenticate(user.make())
        self.assertEqual(self.client.get(self.url).data["key_warnings"], {})

    def test_service_users_without_a_key_record_can_save_a_warning(self):
        actor = user.make(use_service_api_keys=True)
        save_warning(actor, Provider.ELEVENLABS, True)
        self.assertEqual(
            ApiKeys.objects.get(user=actor).key_warnings, {"ELEVENLABS": True}
        )

    def test_unknown_and_custom_providers_do_not_create_builtin_warnings(self):
        save_warning(self.user, "custom-provider", True)
        self.assertEqual(self.client.get(self.url).data["key_warnings"], {})

    def test_warnings_cannot_be_changed_through_the_api(self):
        save_warning(self.user, Provider.OPENAI, True)
        response = self.client.patch(
            self.url, {"key_warnings": {"GEMINI": True}}, format="json"
        )
        self.assertEqual(response.data["key_warnings"], {"OPENAI": True})

    def test_failed_warning_storage_preserves_the_provider_error(self):
        with patch(
            "apps.apikeysmanagement.provider_requests.ApiKeys.objects.select_for_update",
            side_effect=DatabaseError("unavailable"),
        ):
            with self.assertRaises(ProviderRequestError) as raised:
                with openai_request(self.user):
                    raise ProviderRequestError("credentials")
        self.assertEqual(raised.exception.code, "credentials")

    def test_text_sdks_record_401_before_their_error_is_wrapped(self):
        from apps.videomanagement.integrations import llm

        for provider, function, target in [
            (Provider.ANTHROPIC, llm.claude_call, "anthropic.Anthropic"),
            (Provider.GEMINI, llm.gemini_call, "genai.configure"),
        ]:
            with self.subTest(provider=provider):
                error = requests.HTTPError(response=Mock(status_code=401))
                with patch(
                    f"apps.videomanagement.integrations.llm.{target}", side_effect=error
                ):
                    with self.assertRaises(Exception):
                        function("Hello", user=self.user)
                self.assertTrue(
                    self.client.get(self.url).data["key_warnings"][provider]
                )

    def test_builtin_voice_requests_record_401_even_when_generation_catches_the_error(
        self,
    ):
        from apps.videomanagement.integrations import tts

        for provider, implementation in [
            (Provider.ELEVENLABS, tts.ElevenLabsTTSProvider),
            (Provider.SIXTYDB, tts.SixtyDbTTSProvider),
        ]:
            with self.subTest(provider=provider):
                response = Mock(status_code=401)
                response.raise_for_status.side_effect = requests.HTTPError(
                    response=response
                )
                with patch.object(tts.requests, "request", return_value=response):
                    implementation.generate(
                        "Hello", "unused.wav", "test-voice", user=self.user
                    )
                self.assertTrue(
                    self.client.get(self.url).data["key_warnings"][provider]
                )

    def test_builtin_image_requests_record_401_before_reading_the_response(self):
        from apps.videomanagement.integrations.visuals import (
            diffusion,
            google_images,
            midjourney,
        )

        self.keys.diffusion_key = "diffusion-key"
        self.keys.midjourney_key = "midjourney-key"
        self.keys.save()
        for provider, implementation in [
            (Provider.STABLE_DIFFUSION, diffusion.StableDiffusionProvider),
            (Provider.MIDJOURNEY, midjourney.MidjourneyProvider),
        ]:
            with self.subTest(provider=provider):
                response = Mock(status_code=401)
                response.json.return_value = {}
                with patch.object(requests, "request", return_value=response):
                    implementation.generate("Hello", "/tmp/", user=self.user)
                self.assertTrue(
                    self.client.get(self.url).data["key_warnings"][provider]
                )
        with patch.object(requests, "request", return_value=Mock(status_code=401)):
            with self.assertRaises(Exception):
                google_images.make_request({}, user=self.user)
        self.assertTrue(
            self.client.get(self.url).data["key_warnings"][Provider.GOOGLE_SEARCH]
        )

    def test_video_requests_record_401_for_the_providers_shared_key(self):
        from apps.videomanagement.integrations.visuals import video_http

        for provider in [Provider.FAL, Provider.RUNWAY, Provider.GEMINI]:
            with self.subTest(provider=provider):
                response = MagicMock(status_code=401, headers={})
                response.json.return_value = {}
                response.__enter__.return_value = response
                with patch.object(requests, "request", return_value=response):
                    with self.assertRaises(Exception):
                        video_http.json_request(
                            "POST",
                            "https://provider.invalid/",
                            headers={},
                            user=self.user,
                            provider=provider,
                        )
                self.assertTrue(
                    self.client.get(self.url).data["key_warnings"][provider]
                )

    def test_shared_request_forwards_options_and_returns_the_original_response(self):
        response = Mock(status_code=401)
        with patch(
            "apps.apikeysmanagement.provider_requests.requests.request", return_value=response
        ) as send:
            result = provider_request(
                "POST",
                "https://provider.invalid/",
                user=self.user,
                provider=Provider.GEMINI,
                headers={"x-key": "private"},
                json={"prompt": "Hello"},
                timeout=30,
            )
        self.assertIs(result, response)
        send.assert_called_once_with(
            "POST",
            "https://provider.invalid/",
            headers={"x-key": "private"},
            json={"prompt": "Hello"},
            timeout=30,
        )
        self.assertEqual(
            self.client.get(self.url).data["key_warnings"], {"GEMINI": True}
        )

    def test_shared_request_preserves_network_errors_without_marking_the_key(self):
        with patch(
            "apps.apikeysmanagement.provider_requests.requests.request",
            side_effect=requests.ConnectionError("offline"),
        ):
            with self.assertRaises(requests.ConnectionError):
                provider_request(
                    "GET",
                    "https://provider.invalid/",
                    user=self.user,
                    provider=Provider.GEMINI,
                )
        self.assertEqual(self.client.get(self.url).data["key_warnings"], {})

    def test_voice_clone_401_warning_survives_rolling_back_clone_creation(self):
        from apps.videomanagement.exceptions import VoiceProviderError
        from apps.videomanagement.services.voices import cloning

        ApiKeys.objects.filter(user=self.user).update(elevenlabs_key="elevenlabs-key")
        response = Mock(status_code=401)
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
        with (
            patch(
                "apps.apikeysmanagement.provider_requests.requests.request",
                return_value=response,
            ),
            patch.object(cloning, "normalized_sample", return_value=b"audio"),
        ):
            with self.assertRaises(VoiceProviderError):
                cloning.create_clone(self.user, "Narrator", Mock())
        self.assertEqual(
            self.client.get(self.url).data["key_warnings"], {"ELEVENLABS": True}
        )

    def test_resaving_the_same_credential_mode_preserves_warnings(self):
        save_warning(self.user, Provider.OPENAI, True)
        response = self.client.patch(
            self.url, {"use_service_api_keys": False}, format="json"
        )
        self.assertEqual(response.data["key_warnings"], {"OPENAI": True})
