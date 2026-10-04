import os
import tempfile
from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase
from rest_framework.exceptions import APIException

from apps.apikeysmanagement.baker_recipes import user_custom_tts_provider
from apps.usermanagement.baker_recipes import user
from ...utils import tts_utils
from ...utils.tts_utils import ApiSyn, get_voices_from_custom_provider, save


class CustomTtsTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.provider = user_custom_tts_provider.make(
            user=self.user,
            voices_url="https://example.com/voices",
            text_field_name="input",
            voice_field_name="speaker",
        )
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = os.path.join(self.tmp.name, "speech.wav")

    def test_custom_dispatch_uses_the_owners_fields_and_streams_audio_to_disk(self):
        response = MagicMock()
        response.iter_content.return_value = [b"RIFF", b"", b"audio"]
        with patch.object(tts_utils.requests, "post", return_value=response) as post:
            result = save(
                ApiSyn(self.provider.name, "voice-123"),
                "hello",
                self.out,
                user=self.user,
            )
        self.assertEqual(result, self.out)
        with open(self.out, "rb") as audio:
            self.assertEqual(audio.read(), b"RIFFaudio")
        self.assertEqual(
            post.call_args.kwargs["json"], {"input": "hello", "speaker": "voice-123"}
        )
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"], "Bearer secret-api-key"
        )
        self.assertEqual(post.call_args.kwargs["timeout"], tts_utils.DEFAULT_TIMEOUT)
        response.raise_for_status.assert_called_once()

    def test_speech_requests_use_each_configured_authentication_method(self):
        for auth_type, header_name, credential in (
            ("bearer", "", "token"),
            ("header", "x-service-key", "secret"),
            ("basic", "", "alice:pass:word"),
            ("none", "", "unused-secret"),
        ):
            with self.subTest(auth_type=auth_type):
                self.provider.auth_type = auth_type
                self.provider.auth_header_name = header_name
                self.provider.api_key = credential
                self.provider.save()
                response = MagicMock()
                response.iter_content.return_value = [b"audio"]
                with patch.object(
                    tts_utils.requests, "post", return_value=response
                ) as post:
                    tts_utils.tts_from_custom_provider(
                        "hello",
                        self.out,
                        "voice",
                        user=self.user,
                        provider_name=self.provider.name,
                    )
                headers = post.call_args.kwargs["headers"]
                auth = post.call_args.kwargs["auth"]
                if auth_type == "bearer":
                    self.assertEqual(headers["Authorization"], "Bearer token")
                elif auth_type == "header":
                    self.assertEqual(headers["x-service-key"], "secret")
                    self.assertNotIn("Authorization", headers)
                elif auth_type == "basic":
                    self.assertEqual(
                        (auth.username, auth.password), ("alice", "pass:word")
                    )
                else:
                    self.assertNotIn("Authorization", headers)
                    self.assertNotIn("x-service-key", headers)
                    self.assertIsNone(auth)

    def test_extra_parameters_preserve_types_and_cannot_replace_text_or_voice(self):
        parameters = {
            "model": "tts-model",
            "speed": 1.1,
            "options": {"seed": 3},
            "input": "wrong",
            "speaker": "wrong",
        }
        self.provider.extra_parameters = parameters
        self.provider.save()
        response = MagicMock()
        response.iter_content.return_value = [b"audio"]
        with patch.object(tts_utils.requests, "post", return_value=response) as post:
            save(
                ApiSyn(self.provider.name, "voice-123"),
                "hello",
                self.out,
                user=self.user,
            )
        self.assertEqual(
            post.call_args.kwargs["json"],
            {
                "model": "tts-model",
                "speed": 1.1,
                "options": {"seed": 3},
                "input": "hello",
                "speaker": "voice-123",
            },
        )
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.extra_parameters, parameters)

    def test_never_uses_another_users_provider_configuration(self):
        with patch.object(tts_utils.requests, "post") as post:
            with self.assertRaises(APIException):
                save(
                    ApiSyn(self.provider.name, "voice"),
                    "hello",
                    self.out,
                    user=user.make(),
                )
            post.assert_not_called()

    def test_missing_user_or_provider_is_rejected_before_a_network_request(self):
        with patch.object(tts_utils.requests, "post") as post:
            for owner, name in (
                (None, self.provider.name),
                (self.user, None),
                (self.user, "missing"),
            ):
                with self.subTest(provider=name, user=owner):
                    with self.assertRaises(APIException):
                        tts_utils.tts_from_custom_provider(
                            "hello", self.out, "voice", user=owner, provider_name=name
                        )
            post.assert_not_called()

    def test_http_failure_or_timeout_does_not_produce_an_audio_path(self):
        for failure in (requests.HTTPError("401"), requests.Timeout("timed out")):
            with self.subTest(failure=type(failure).__name__):
                response = MagicMock()
                response.raise_for_status.side_effect = failure
                with patch.object(tts_utils.requests, "post", return_value=response):
                    result = save(
                        ApiSyn(self.provider.name, "voice"),
                        "hello",
                        self.out,
                        user=self.user,
                    )
                self.assertIsNone(result)
                self.assertFalse(os.path.exists(self.out))

    def test_a_connection_failure_does_not_produce_an_audio_path(self):
        with patch.object(
            tts_utils.requests, "post", side_effect=requests.ConnectionError("offline")
        ):
            self.assertIsNone(
                save(
                    ApiSyn(self.provider.name, "voice"),
                    "hello",
                    self.out,
                    user=self.user,
                )
            )
        self.assertFalse(os.path.exists(self.out))

    def test_voice_listing_accepts_a_list_or_the_supported_envelopes(self):
        voices = [{"id": "voice-123", "name": "My voice"}]
        for payload in (voices, {"voices": voices}, {"data": voices}, {}):
            with self.subTest(payload=payload):
                response = MagicMock()
                response.json.return_value = payload
                with patch.object(
                    tts_utils.requests, "get", return_value=response
                ) as get:
                    actual = get_voices_from_custom_provider(
                        self.user, self.provider.name
                    )
                self.assertEqual(actual, [] if payload == {} else voices)
                get.assert_called_once_with(
                    self.provider.voices_url, timeout=tts_utils.DEFAULT_TIMEOUT
                )
                response.raise_for_status.assert_called_once()

    def test_a_provider_without_a_voices_url_makes_no_network_request(self):
        self.provider.voices_url = ""
        self.provider.save()
        with patch.object(tts_utils.requests, "get") as get:
            self.assertIsNone(
                get_voices_from_custom_provider(self.user, self.provider.name)
            )
            get.assert_not_called()

    def test_voice_listing_never_reads_another_users_endpoint(self):
        with patch.object(tts_utils.requests, "get") as get:
            with self.assertRaises(self.provider.DoesNotExist):
                get_voices_from_custom_provider(user.make(), self.provider.name)
            get.assert_not_called()

    def test_voice_listing_handles_http_errors_invalid_json_and_timeouts(self):
        for failure in (
            requests.HTTPError("403"),
            ValueError("invalid JSON"),
            requests.Timeout("timed out"),
        ):
            with self.subTest(failure=type(failure).__name__):
                with patch.object(tts_utils.requests, "get", side_effect=failure):
                    self.assertIsNone(
                        get_voices_from_custom_provider(self.user, self.provider.name)
                    )

    def test_interrupted_audio_stream_does_not_leave_a_successful_partial_file(self):
        def interrupted_stream(*args, **kwargs):
            yield b"partial audio"
            raise requests.ConnectionError("stream interrupted")

        response = MagicMock()
        response.iter_content.side_effect = interrupted_stream
        with patch.object(tts_utils.requests, "post", return_value=response):
            self.assertIsNone(
                save(
                    ApiSyn(self.provider.name, "voice"),
                    "hello",
                    self.out,
                    user=self.user,
                )
            )
        self.assertFalse(os.path.exists(self.out))

    def test_an_empty_audio_response_is_not_returned_as_a_generated_file(self):
        response = MagicMock()
        response.iter_content.return_value = []
        with patch.object(tts_utils.requests, "post", return_value=response):
            self.assertIsNone(
                save(
                    ApiSyn(self.provider.name, "voice"),
                    "hello",
                    self.out,
                    user=self.user,
                )
            )
