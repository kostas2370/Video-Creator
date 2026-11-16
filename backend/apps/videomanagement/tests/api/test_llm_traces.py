import json
from io import StringIO
from unittest.mock import patch

from django.db import DatabaseError
from django.urls import reverse
from rest_framework.exceptions import APIException

from apps.usage.models import LLMTrace
from apps.usage.services import video_usage
from apps.usermanagement.baker_recipes import user
from apps.videomanagement.integrations.llm import get_raw_reply, get_reply

from .base import ApiTestCase


class LLMTraceTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for()
        self.url = reverse("video-llm-traces", args=[self.video.pk])
        self.answer = {
            "title": "Title",
            "scenes": [
                {
                    "scene": "Scene",
                    "sentences": [{"sentence": "Hello", "image_description": "A fox"}],
                }
            ],
        }

    def test_records_actual_retry_prompts_and_raw_responses(self):
        raw = json.dumps(self.answer)
        with (
            video_usage(self.video),
            patch(
                "apps.videomanagement.integrations.llm.official_gpt_call",
                side_effect=[StringIO("invalid JSON"), StringIO(raw)],
            ),
        ):
            self.assertEqual(
                get_reply("Original prompt", gpt_model="gpt-test", user=self.user),
                self.answer,
            )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        traces = response.data["results"]
        self.assertEqual(len(traces), 2)
        self.assertEqual(traces[0]["response"], raw)
        self.assertIn("CORRECTION REQUIRED:", traces[0]["prompt"])
        self.assertEqual(traces[0]["attempt"], 2)
        self.assertEqual(traces[0]["validation_errors"], [])
        self.assertEqual(traces[1]["prompt"], "Original prompt")
        self.assertEqual(traces[1]["response"], "invalid JSON")
        self.assertTrue(traces[1]["validation_errors"])

    def test_owner_only_and_paginated(self):
        LLMTrace.objects.bulk_create(
            [
                LLMTrace(
                    video=self.video, model="gpt-test", attempt=1, prompt=f"Prompt {i}"
                )
                for i in range(13)
            ]
        )
        data = self.client.get(self.url).data
        self.assertEqual(data["count"], 13)
        self.assertEqual(len(data["results"]), 12)
        self.assertEqual(data["next"], 2)
        self.client.force_authenticate(user.make(is_superuser=False))
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(self.url).status_code, (401, 403))

    def test_raw_text_requests_keep_their_project_trace(self):
        with (
            video_usage(self.video),
            patch(
                "apps.videomanagement.integrations.llm.official_gpt_call",
                return_value=StringIO("  A rewritten sentence.\n"),
            ),
        ):
            response = get_raw_reply(
                "Rewrite this", gpt_model="gpt-test", user=self.user
            )
        self.assertEqual(response, "A rewritten sentence.")
        trace = LLMTrace.objects.get()
        self.assertEqual(trace.prompt, "Rewrite this")
        self.assertEqual(trace.response, "  A rewritten sentence.\n")
        self.assertEqual(trace.model, "gpt-test")
        self.assertEqual(trace.validation_errors, [])

    def test_wrong_owner_context_and_unscoped_calls_are_not_captured(self):
        with patch(
            "apps.videomanagement.integrations.llm.official_gpt_call",
            return_value=StringIO("hello"),
        ):
            get_raw_reply("prompt", user=self.user)
            with video_usage(self.video):
                get_raw_reply("prompt", user=user.make())
        self.assertFalse(LLMTrace.objects.exists())

    def test_failed_provider_attempt_is_recorded_without_provider_error_details(self):
        with (
            video_usage(self.video),
            patch(
                "apps.videomanagement.integrations.llm.official_gpt_call",
                side_effect=APIException("sensitive provider details"),
            ),
            self.assertRaises(APIException),
        ):
            get_reply("prompt", user=self.user)
        trace = LLMTrace.objects.get()
        self.assertEqual(trace.validation_errors, ["Provider request failed."])
        self.assertEqual(trace.response, "")

    def test_trace_storage_failure_does_not_discard_a_valid_response(self):
        with (
            video_usage(self.video),
            patch(
                "apps.usage.llm_traces.LLMTrace.objects.create",
                side_effect=DatabaseError,
            ),
            patch(
                "apps.videomanagement.integrations.llm.official_gpt_call",
                return_value=StringIO(json.dumps(self.answer)),
            ),
        ):
            self.assertEqual(get_reply("prompt", user=self.user), self.answer)
        self.assertEqual(self.client.get(self.url).status_code, 200)
