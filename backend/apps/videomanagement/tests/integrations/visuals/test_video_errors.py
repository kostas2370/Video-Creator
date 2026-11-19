"""Public diagnostics must be useful without copying private upstream content."""

import logging
from unittest.mock import MagicMock, patch

import requests
from celery import Celery
from celery.backends.base import Backend
from django.test import SimpleTestCase

from apps.videomanagement.integrations.visuals import video_http as http
from apps.videomanagement.integrations.visuals.errors import (
    VideoProviderError,
    provider_error,
    public_video_error,
)


class VideoErrorTests(SimpleTestCase):
    def response(self, payload, status=400):
        result = MagicMock(status_code=status)
        result.json.return_value = payload
        return result

    def test_numeric_code_and_unknown_status_do_not_hide_recognized_type(self):
        response = self.response(
            {
                "error": {
                    "code": 400,
                    "status": "Bad Request",
                    "type": "content_policy_violation",
                    "message": "secret-key signed-url private prompt",
                }
            }
        )
        message = provider_error(response)
        self.assertIn("CONTENT_BLOCKED", message)
        self.assertIn("replace the starting frame", message)
        self.assertNotIn("secret-key", message)
        self.assertNotIn("private prompt", message)

    def test_message_only_errors_are_classified_without_echoing_the_message(self):
        for message, expected in (
            (
                "Request blocked by safety filters: private prompt secret-key",
                "CONTENT_BLOCKED",
            ),
            (
                "Billing must be enabled. https://private.example/?token=secret",
                "FAILED_PRECONDITION",
            ),
            ("Rate limit exceeded for private account", "RESOURCE_EXHAUSTED"),
        ):
            with self.subTest(expected=expected):
                result = provider_error(
                    self.response({"error": {"code": 400, "message": message}})
                )
                self.assertIn(expected, result)
                self.assertNotIn("secret", result)
                self.assertNotIn("private", result)

    def test_known_field_violations_get_specific_guidance_without_descriptions(self):
        response = self.response(
            {
                "error": {
                    "status": "INVALID_ARGUMENT",
                    "details": [
                        {
                            "fieldViolations": [
                                {
                                    "field": "response_format.duration",
                                    "description": "secret-key private prompt",
                                }
                            ]
                        }
                    ],
                }
            }
        )
        message = provider_error(response)
        self.assertIn("requested video length", message)
        self.assertNotIn("private prompt", message)
        self.assertNotIn("secret-key", message)

    def test_unknown_and_malformed_details_are_not_exposed(self):
        for details in (
            None,
            [None, "secret"],
            [{"fieldViolations": "secret"}],
            [{"fieldViolations": [{"field": ["secret"]}]}],
        ):
            with self.subTest(details=details):
                message = provider_error(
                    self.response(
                        {"error": {"status": "INVALID_ARGUMENT", "details": details}}
                    )
                )
                self.assertIn("request parameters", message)
                self.assertNotIn("secret", message)
        message = provider_error(
            self.response({"error": {"message": "private prompt secret-key"}})
        )
        self.assertIn("did not supply a recognized reason", message)
        self.assertNotIn("private prompt", message)

    def test_http_fallbacks_distinguish_rate_limits_and_server_failures(self):
        self.assertIn("rate limiting", provider_error(self.response({}, 429)))
        self.assertIn("server problem", provider_error(self.response({}, 503)))

    def test_http_error_reference_is_logged_without_raw_response_or_credentials(self):
        response = self.response(
            {
                "error": {
                    "code": "content_blocked",
                    "message": "secret-key private prompt https://private.example",
                }
            }
        )
        with (
            patch.object(http.requests, "request", return_value=response),
            self.assertLogs(http.logger, logging.WARNING) as logs,
        ):
            response.__enter__.return_value = response
            with self.assertRaises(VideoProviderError) as caught:
                http.json_request(
                    "POST",
                    "https://example.test",
                    headers={"Authorization": "secret-key"},
                )
        self.assertIn("Reference:", str(caught.exception))
        self.assertIn(str(caught.exception), logs.output[0])
        self.assertNotIn("secret-key", logs.output[0])
        self.assertNotIn("private prompt", logs.output[0])

    def test_safe_error_survives_celery_json_exception_roundtrip(self):
        backend = Backend(app=Celery("safe-video-error"), serializer="json")
        original = VideoProviderError("Gemini: safety filters blocked the request.")
        restored = backend.exception_to_python(backend.prepare_exception(original))
        self.assertIsInstance(restored, VideoProviderError)
        self.assertEqual(public_video_error(restored), str(original))
        self.assertIsNone(public_video_error(RuntimeError("private provider error")))

    def test_network_failures_have_actionable_messages_without_transport_details(self):
        for error, expected in (
            (requests.Timeout("secret-url"), "timed out"),
            (requests.ConnectionError("secret-key"), "Could not connect"),
        ):
            with self.subTest(error=type(error).__name__):
                call = http.guarded("Gemini")(MagicMock(side_effect=error))
                with self.assertRaises(VideoProviderError) as caught:
                    call()
                self.assertIn(expected, str(caught.exception))
                self.assertNotIn("secret", str(caught.exception))

    def test_async_failure_preserves_recognized_provider_reason(self):
        with self.assertRaisesRegex(VideoProviderError, "CONTENT_BLOCKED"):
            http.poll(
                lambda: {
                    "status": "done",
                    "error": {"code": "content_blocked", "message": "private"},
                },
                field="status",
                completed={"done"},
                pending={"pending"},
                label="Gemini",
            )

    def test_specific_structured_reason_takes_priority_over_generic_status(self):
        message = provider_error(
            self.response(
                {
                    "error": {
                        "status": "INVALID_ARGUMENT",
                        "details": [{"reason": "CONTENT_BLOCKED"}],
                    }
                }
            )
        )
        self.assertIn("CONTENT_BLOCKED", message)

    def test_failure_status_reports_provider_reason_before_poll_completion(self):
        with self.assertRaisesRegex(VideoProviderError, "PAYMENT_REQUIRED"):
            http.poll(
                lambda: {"status": "FAILED", "error": {"code": "payment_required"}},
                completed={"DONE"},
                pending={"RUNNING"},
                label="Gemini",
            )

    def test_documented_generation_block_codes_are_actionable_and_private(self):
        for code, expected in (
            ("safety", "safety filters"),
            ("image_safety", "starting frame"),
            ("prohibited_content", "safety filters"),
            ("blocklist", "safety filters"),
            ("recitation", "copyright"),
            ("language", "unsupported language"),
            ("spii", "sensitive personal information"),
        ):
            with self.subTest(code=code):
                result = provider_error(
                    self.response(
                        {
                            "error": {
                                "code": code,
                                "message": "private prompt secret-key",
                            }
                        }
                    )
                )
                self.assertIn(expected, result)
                self.assertNotIn("private", result)
                self.assertNotIn("secret-key", result)
