from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from apps.publishing.http import ProviderError, request_json
from apps.publishing.diagnostics import log_failure


class PlatformRequestTests(SimpleTestCase):
    def test_oauth_error_status_and_allowlisted_code_are_available_without_raw_details(self):
        response = Mock(status_code=400)
        response.json.return_value = {"error": "invalid_grant", "error_description": "token=secret"}
        with patch("apps.publishing.http.requests.request", return_value=response):
            with self.assertRaises(ProviderError) as caught:
                request_json("POST", "https://platform.test")
        self.assertEqual(caught.exception.provider_code, "invalid_grant")
        self.assertEqual(caught.exception.http_status, 400)
        with self.assertLogs("apps.publishing", level="WARNING") as logs:
            log_failure("oauth_callback", platform="tiktok", reference="callback", error=caught.exception)
        self.assertIn("invalid_grant", logs.output[0])
        self.assertNotIn("secret", logs.output[0])

    def test_arbitrary_provider_error_codes_are_not_logged(self):
        error = ProviderError("safe message", code="secret-in-code", status=400)
        with self.assertLogs("apps.publishing", level="WARNING") as logs:
            log_failure("oauth_callback", platform="tiktok", reference="callback", error=error)
        self.assertIsNone(error.provider_code)
        self.assertNotIn("secret", logs.output[0])

    def test_success_responses_include_tiktok_success_markers(self):
        for data in ({"id": "video"}, {"error": {"code": "ok"}}, {"error": {"code": 0}}):
            with self.subTest(data=data), patch("apps.publishing.http.requests.request", return_value=Mock(status_code=200, json=Mock(return_value=data))) as request:
                self.assertEqual(request_json("GET", "https://platform.test", token="private", headers={"Accept": "application/json"}), data)
                self.assertEqual(request.call_args.kwargs["headers"], {"Accept": "application/json", "Authorization": "Bearer private"})
                self.assertFalse(request.call_args.kwargs["allow_redirects"])

    def test_http_success_does_not_hide_platform_errors_or_invalid_response_shapes(self):
        for data in ({"error": {"code": "access_denied", "message": "secret"}}, {"error": "secret"}, ["secret"]):
            with self.subTest(data=data), patch("apps.publishing.http.requests.request", return_value=Mock(status_code=200, json=Mock(return_value=data))):
                with self.assertRaises(ProviderError) as caught:
                    request_json("GET", "https://platform.test")
                self.assertNotIn("secret", str(caught.exception))

    def test_network_and_invalid_json_errors_are_sanitized(self):
        for error in (requests.Timeout("token=secret"), ValueError("secret response")):
            with self.subTest(error=type(error).__name__), patch("apps.publishing.http.requests.request") as request:
                if isinstance(error, requests.RequestException):
                    request.side_effect = error
                else:
                    request.return_value.status_code = 200
                    request.return_value.json.side_effect = error
                with self.assertRaises(ProviderError) as caught:
                    request_json("GET", "https://platform.test")
                self.assertNotIn("secret", str(caught.exception))
