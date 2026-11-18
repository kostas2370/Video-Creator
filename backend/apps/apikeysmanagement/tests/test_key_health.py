from unittest.mock import Mock, patch

import requests
from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.common.provider_errors import ProviderRequestError
from apps.usermanagement.baker_recipes import user

from ..baker_recipes import api_keys
from ..key_health import key_request, openai_request, record_response, save_warning
from ..models import ApiKeys, Provider


class KeyHealthTests(TestCase):
    def setUp(self):
        self.user = user.make(use_service_api_keys=False)
        self.keys = api_keys.make(user=self.user, openai_key="sk-private-rejected-key")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse("api-keys")

    def test_401_responses_set_a_separate_warning_for_each_builtin_key(self):
        providers = set(ApiKeys.FIELDS) - {Provider.GOOGLE_SEARCH_ENGINE_ID}
        for provider in providers:
            record_response(self.user, provider, Mock(status_code=401))
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
            record_response(self.user, Provider.OPENAI, Mock(status_code=status))
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
        record_response(self.user, Provider.GEMINI, Mock(status_code=200))
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
            "apps.apikeysmanagement.key_health.ApiKeys.objects.select_for_update",
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
                with patch.object(tts.requests, "post", return_value=response):
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
                with patch.object(requests, "post", return_value=response):
                    implementation.generate("Hello", "/tmp/", user=self.user)
                self.assertTrue(
                    self.client.get(self.url).data["key_warnings"][provider]
                )
        with patch.object(requests, "get", return_value=Mock(status_code=401)):
            with self.assertRaises(Exception):
                google_images.make_request({}, user=self.user)
        self.assertTrue(
            self.client.get(self.url).data["key_warnings"][Provider.GOOGLE_SEARCH]
        )

    def test_video_requests_record_401_for_the_providers_shared_key(self):
        from apps.videomanagement.integrations.visuals import video_http

        for provider in [Provider.FAL, Provider.RUNWAY, Provider.GEMINI]:
            with self.subTest(provider=provider):
                response = Mock(status_code=401, headers={})
                response.json.return_value = {}
                with patch.object(requests, "request") as request:
                    request.return_value.__enter__.return_value = response
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
