import asyncio
import io
import json
import logging
from contextlib import contextmanager
from unittest.mock import patch

from celery import shared_task
from celery.signals import before_task_publish
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import path
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from video_creator.observability import (
    JsonFormatter,
    current_request_id,
    request_context,
    request_logging,
)


class LoggingView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, kind):
        if kind == "crash":
            raise RuntimeError("private provider detail")
        if kind == "unavailable":
            raise APIException("Try again later")
        if kind == "invalid":
            raise ValidationError({"title": "Required"})
        return Response({"ok": True})


urlpatterns = [path("api/log-test/<str:kind>/", LoggingView.as_view())]


@contextmanager
def captured_json():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("video_creator.exceptions")
    previous_level = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        yield stream
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


@override_settings(ROOT_URLCONF=__name__)
class ObservabilityTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_server_error_has_safe_message_and_matching_log_reference(self):
        with captured_json() as output:
            response = self.client.get(
                "/api/log-test/crash/?token=secret", HTTP_AUTHORIZATION="secret"
            )
        self.assertEqual(response.status_code, 500)
        reference = response["X-Request-ID"]
        self.assertRegex(reference, r"^[a-f0-9]{32}$")
        self.assertEqual(response.data["request_id"], reference)
        self.assertNotIn("private provider detail", str(response.data))
        records = [json.loads(line) for line in output.getvalue().splitlines()]
        failure = next(row for row in records if row["message"] == "api_request_failed")
        self.assertEqual(failure["request_id"], reference)
        self.assertIn("RuntimeError: private provider detail", failure["exception"])
        self.assertEqual(failure["method"], "GET")
        self.assertNotIn("secret", output.getvalue())
        self.assertIsNone(current_request_id())

    def test_validation_and_handled_server_errors_keep_their_contract(self):
        invalid = self.client.get("/api/log-test/invalid/")
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.data, {"title": "Required"})
        unavailable = self.client.get("/api/log-test/unavailable/")
        self.assertEqual(unavailable.status_code, 500)
        self.assertEqual(unavailable.data["detail"], "Try again later")
        self.assertEqual(unavailable.data["request_id"], unavailable["X-Request-ID"])

    def test_requests_have_distinct_references_and_ignore_incoming_ids(self):
        first = self.client.get("/api/log-test/ok/", HTTP_X_REQUEST_ID="spoofed")
        second = self.client.get("/api/log-test/ok/")
        self.assertEqual(first.status_code, 200)
        self.assertNotEqual(first["X-Request-ID"], "spoofed")
        self.assertNotEqual(first["X-Request-ID"], second["X-Request-ID"])
        self.assertIsNone(request_context.get())

    def test_async_requests_keep_separate_context_and_clear_it_after_failure(self):
        async def exercise():
            async def response(request):
                await asyncio.sleep(0)
                self.assertEqual(current_request_id(), request.request_id)
                return HttpResponse()

            middleware = request_logging(response)
            requests = [RequestFactory().get("/api/test/") for _ in range(2)]
            responses = await asyncio.gather(
                *(middleware(request) for request in requests)
            )
            self.assertNotEqual(
                responses[0]["X-Request-ID"], responses[1]["X-Request-ID"]
            )
            self.assertIsNone(current_request_id())

            async def crash(request):
                raise RuntimeError("test")

            with self.assertRaises(RuntimeError):
                await request_logging(crash)(requests[0])
            self.assertIsNone(current_request_id())

        asyncio.run(exercise())

    def test_django_logs_keep_reference_after_middleware_context_is_closed(self):
        request = RequestFactory().get("/api/test/")
        request.request_id = "b" * 32
        record = logging.LogRecord(
            "django.request", logging.ERROR, "test.py", 1, "Server error", (), None
        )
        record.request = request
        row = json.loads(JsonFormatter().format(record))
        self.assertEqual(row["request_id"], request.request_id)
        del request.request_id
        self.assertNotIn("request_id", json.loads(JsonFormatter().format(record)))

    def test_publication_and_worker_logs_share_the_request_reference(self):
        @shared_task(name="test.observability")
        def task():
            pass

        request = RequestFactory().post("/api/test/", data={"password": "hidden"})
        request.request_id = "a" * 32
        token = request_context.set(request)
        headers = {}
        try:
            before_task_publish.send(sender=task.name, headers=headers)
        finally:
            request_context.reset(token)
        self.assertEqual(headers["request_id"], request.request_id)
        task.push_request(id="worker-id", headers=headers)
        try:
            with patch("video_creator.observability.current_task", task):
                record = logging.LogRecord(
                    "worker", logging.ERROR, "test.py", 1, "Job failed", (), None
                )
                row = json.loads(JsonFormatter().format(record))
                self.assertEqual(row["request_id"], request.request_id)
                self.assertEqual(row["task_id"], "worker-id")
                self.assertEqual(row["task_name"], task.name)
                nested = {}
                before_task_publish.send(sender=task.name, headers=nested)
                self.assertEqual(nested["request_id"], request.request_id)
        finally:
            task.pop_request()
        self.assertIsNone(current_request_id())
