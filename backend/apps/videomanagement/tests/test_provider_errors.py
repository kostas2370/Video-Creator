import pickle
from unittest.mock import patch

from celery import current_app
from celery.backends.base import Backend
from django.test import SimpleTestCase, TestCase

from httpx2 import Request, Response
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from apps.apikeysmanagement.models import Provider
from apps.apikeysmanagement.provider_requests import key_request
from apps.common.provider_errors import (
    ProviderRequestError,
    provider_failure,
)
from apps.videomanagement.baker_recipes import video
from apps.videomanagement.integrations import llm
from apps.videomanagement.services.draft_jobs import _task_error
from apps.videomanagement.tasks import generate_video_task
from video_creator.exceptions import api_exception_handler


def openai_request():
    return Request("POST", "https://api.openai.com/v1/responses")


def openai_response(status):
    return Response(status, request=openai_request())


def rejected_key():
    return AuthenticationError(
        "Incorrect API key: sk-private-secret",
        response=openai_response(401),
        body={"code": "invalid_api_key"},
    )


class ProviderErrorTests(SimpleTestCase):
    def test_rejected_credentials_are_actionable_without_exposing_provider_details(
        self,
    ):
        failure = provider_failure(rejected_key())
        self.assertEqual(failure["code"], "credentials")
        self.assertIn("expired", failure["message"])
        self.assertIn("API keys settings", failure["message"])
        self.assertNotIn("sk-private", str(failure))

    def test_quota_is_distinguished_from_temporary_rate_limits(self):
        for reason, expected in [
            ("insufficient_quota", "quota"),
            ("rate_limit_exceeded", "rate_limit"),
        ]:
            error = RateLimitError(
                "private",
                response=openai_response(429),
                body={"code": reason},
            )
            self.assertEqual(provider_failure(error)["code"], expected)

    def test_http_statuses_use_known_messages_and_leave_other_errors_unclassified(self):
        for status, expected in [
            (401, "credentials"),
            (403, "access"),
            (429, "rate_limit"),
            (503, "unavailable"),
            (400, None),
        ]:
            with self.subTest(status=status):
                error = APIStatusError(
                    "private", response=openai_response(status), body=None
                )
                failure = provider_failure(error)
                self.assertEqual(failure["code"] if failure else None, expected)

    def test_nested_quota_details_take_precedence_over_http_status(self):
        error = APIStatusError(
            "private",
            response=openai_response(429),
            body={"error": {"code": "insufficient_quota"}},
        )
        self.assertEqual(provider_failure(error)["code"], "quota")

    def test_timeouts_are_distinct_from_connection_failures(self):
        for error, expected in [
            (APITimeoutError(request=openai_request()), "timeout"),
            (APIConnectionError(request=openai_request()), "connection"),
        ]:
            with self.subTest(expected=expected):
                self.assertEqual(provider_failure(error)["code"], expected)

    def test_exception_chains_are_followed_without_looping_on_cycles(self):
        outer = RuntimeError("private")
        outer.__cause__ = rejected_key()
        self.assertEqual(provider_failure(outer)["code"], "credentials")
        outer.__cause__ = outer
        self.assertIsNone(provider_failure(outer))

    def test_request_context_preserves_an_already_normalized_error(self):
        error = ProviderRequestError("credentials")
        with self.assertRaises(ProviderRequestError) as raised:
            with key_request(None, Provider.OPENAI):
                raise error
        self.assertIs(raised.exception, error)

    def test_safe_errors_survive_celery_and_pickle_serialization(self):
        error = ProviderRequestError("credentials")
        backend = Backend(app=current_app)
        encoded = backend.prepare_exception(error, serializer="json")
        decoded = backend.exception_to_python(encoded)
        for recovered in [pickle.loads(pickle.dumps(error)), decoded]:
            self.assertEqual(provider_failure(recovered)["code"], "credentials")
            self.assertIn("OpenAI rejected", _task_error(recovered))

    def test_sdk_errors_wrapped_by_the_script_integration_stay_actionable(self):
        with patch.object(llm, "OpenAI", side_effect=rejected_key()):
            with self.assertRaises(ProviderRequestError) as raised:
                llm.official_gpt_call("Hello")
        self.assertEqual(raised.exception.code, "credentials")

    def test_api_failures_are_provider_errors_instead_of_login_failures(self):
        response = api_exception_handler(rejected_key(), {})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["provider_error"]["code"], "credentials")
        self.assertNotIn("sk-private", str(response.data))

    def test_unknown_errors_remain_generic(self):
        self.assertIsNone(provider_failure(RuntimeError("sk-private-secret")))
        self.assertNotIn("sk-private", _task_error(RuntimeError("sk-private-secret")))

    def test_provider_boundary_preserves_unknown_exceptions(self):
        with self.assertRaisesMessage(ValueError, "invalid local input"):
            with key_request(None, Provider.OPENAI):
                raise ValueError("invalid local input")


class SavedProviderErrorTests(TestCase):
    def test_generation_failure_is_saved_for_project_reload(self):
        project = video.make(status="GENERATION")
        with patch(
            "apps.videomanagement.services.videos.generation.generate_video",
            side_effect=ProviderRequestError("credentials"),
        ):
            with self.assertRaises(ProviderRequestError):
                generate_video_task(video_id=project.pk)
        project.refresh_from_db()
        self.assertEqual(project.status, "FAILED")
        self.assertEqual(project.generation_error["code"], "credentials")
        self.assertEqual(project.render_error, {})

    def test_retry_clears_the_previous_failure(self):
        project = video.make(
            status="GENERATION", generation_error={"message": "Old error"}
        )
        with patch("apps.videomanagement.services.videos.generation.generate_video"):
            generate_video_task(video_id=project.pk)
        project.refresh_from_db()
        self.assertEqual(project.generation_error, {})
