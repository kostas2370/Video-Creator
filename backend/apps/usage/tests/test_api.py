from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import APIException
from rest_framework.test import APIClient

from apps.usage.models import AIUsage
from apps.usage.serializers import UsageSerializer
from apps.usage.services import record_usage
from apps.usermanagement.baker_recipes import user
from apps.videomanagement.integrations import llm as llm
from apps.videomanagement.integrations import tts as tts_utils
from apps.videomanagement.integrations.visuals import openai_images


class UsageTests(TestCase):
    def test_partial_token_metrics_keep_independent_availability(self):
        for model, usage in (
            ("input-only", {"input_tokens": 12}),
            ("total-only", {"total_tokens": 20}),
        ):
            record_usage(self.user, "text", "OPENAI", model, usage)
        data = self.client.get(reverse("ai_usage")).data
        rows = {row["model"]: row for row in data["breakdown"]}
        self.assertEqual(rows["input-only"]["input_tokens"], 12)
        self.assertIsNone(rows["input-only"]["output_tokens"])
        self.assertIsNone(rows["input-only"]["total_tokens"])
        self.assertIsNone(rows["total-only"]["input_tokens"])
        self.assertEqual(rows["total-only"]["total_tokens"], 20)
        self.assertEqual(data["totals"]["requests_with_input_tokens"], 1)
        self.assertEqual(data["totals"]["requests_with_output_tokens"], 0)
        self.assertEqual(data["totals"]["requests_with_tokens"], 1)
        self.assertIsNone(data["totals"]["output_tokens"])

    def test_reported_zero_is_distinct_from_unreported_usage_in_same_group(self):
        record_usage(self.user, "text", "OPENAI", "model", {"input_tokens": 0})
        record_usage(self.user, "text", "OPENAI", "model")
        row = self.client.get(reverse("ai_usage")).data["breakdown"][0]
        self.assertEqual(row["input_tokens"], 0)
        self.assertEqual(row["requests_with_input_tokens"], 1)
        self.assertEqual(row["requests"], 2)
        self.assertIsNone(row["output_tokens"])

    def setUp(self):
        self.user = user.make(use_service_api_keys=True)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_summary_preserves_scope_and_serialization_performs_no_queries(self):
        record_usage(
            self.user,
            "text",
            "OPENAI",
            "gpt-test",
            {"input_tokens": 10, "output_tokens": 2},
        )
        record_usage(self.user, "text", "OPENAI", "gpt-test")
        record_usage(self.user, "tts", "OPENAI", characters=20)
        record_usage(user.make(), "text", "OPENAI", "gpt-test", {"total_tokens": 999})
        usage = AIUsage.objects.filter(user=self.user, service="text")
        with self.assertNumQueries(2):
            summary = usage.summary()
        summary.update(period="all", first_recorded_at=usage.first_recorded_at())
        with self.assertNumQueries(0):
            result = UsageSerializer(summary).data
        self.assertEqual(result["totals"]["requests"], 2)
        self.assertEqual(result["totals"]["requests_with_tokens"], 1)
        self.assertEqual(result["totals"]["total_tokens"], 12)
        self.assertEqual(result["totals"]["characters"], 0)
        self.assertEqual(len(result["breakdown"]), 1)
        self.assertEqual(result["breakdown"][0]["total_tokens"], 12)

    def test_normalizes_provider_tokens_and_preserves_unknowns(self):
        record_usage(
            self.user,
            "text",
            "OPENAI",
            "gpt-test",
            {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
        )
        record_usage(
            self.user,
            "text",
            "ANTHROPIC",
            "claude-test",
            SimpleNamespace(
                input_tokens=10, output_tokens=5, cache_read_input_tokens=7
            ),
        )
        record_usage(
            self.user,
            "text",
            "GEMINI",
            "gemini-test",
            SimpleNamespace(
                prompt_token_count=3, candidates_token_count=4, total_token_count=9
            ),
        )
        record_usage(self.user, "tts", "custom", characters=42, custom=True)
        rows = list(AIUsage.objects.order_by("id"))
        self.assertEqual([row.total_tokens for row in rows], [20, 22, 9, None])
        self.assertEqual(rows[3].characters, 42)
        self.assertEqual(rows[3].key_source, "personal")

    def test_usage_is_private_and_groups_by_model_and_key_source(self):
        record_usage(
            self.user,
            "text",
            "OPENAI",
            "gpt-test",
            {"input_tokens": 10, "output_tokens": 2},
        )
        self.user.use_service_api_keys = False
        record_usage(
            self.user,
            "text",
            "OPENAI",
            "gpt-test",
            {"input_tokens": 3, "output_tokens": 4},
        )
        record_usage(user.make(), "text", "OPENAI", "other", {"total_tokens": 999})
        response = self.client.get(reverse("ai_usage"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["totals"]["total_tokens"], 19)
        self.assertEqual(response.data["totals"]["requests"], 2)
        self.assertEqual(
            {row["key_source"] for row in response.data["breakdown"]},
            {"personal", "service"},
        )

    def test_filters_period_and_rejects_invalid_period(self):
        record_usage(self.user, "tts", "OPENAI", characters=5)
        AIUsage.objects.update(created_at=timezone.now() - timedelta(days=10))
        record_usage(self.user, "images", "OPENAI", images=1)
        for period, expected in [("7", 1), ("30", 2), ("all", 2)]:
            response = self.client.get(reverse("ai_usage"), {"period": period})
            self.assertEqual(response.data["totals"]["requests"], expected)
        self.assertEqual(
            self.client.get(reverse("ai_usage"), {"period": "bad"}).status_code, 400
        )

    def test_requires_authentication_and_returns_zero_totals_when_empty(self):
        response = self.client.get(reverse("ai_usage"))
        self.assertEqual(response.data["totals"]["total_tokens"], 0)
        self.assertEqual(response.data["breakdown"], [])
        self.assertIsNone(response.data["first_recorded_at"])
        self.assertEqual(response.data["period"], "30")
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(reverse("ai_usage")).status_code, [401, 403])

    def test_default_period_excludes_old_records_but_preserves_first_recorded_date(
        self,
    ):
        record_usage(self.user, "tts", "OPENAI", characters=5)
        first = timezone.now() - timedelta(days=40)
        AIUsage.objects.update(created_at=first)
        response = self.client.get(reverse("ai_usage"))
        self.assertEqual(response.data["totals"]["requests"], 0)
        self.assertEqual(response.data["breakdown"], [])
        self.assertEqual(response.data["period"], "30")

        self.assertEqual(parse_datetime(response.data["first_recorded_at"]), first)

    def test_filterset_rejects_empty_and_invalid_periods(self):
        for period in ("", "0", "-7", "31", "invalid"):
            response = self.client.get(reverse("ai_usage"), {"period": period})
            self.assertEqual(response.status_code, 400)
            self.assertIn("period", response.data)

    def test_measurement_failure_does_not_break_generation_or_transaction(self):
        with patch(
            "apps.usage.services.AIUsage.objects.create",
            side_effect=DatabaseError,
        ):
            record_usage(self.user, "text", "OPENAI")
        self.assertEqual(AIUsage.objects.count(), 0)

    def test_stream_accepts_usage_only_final_chunk_and_records_once(self):
        client = MagicMock()
        client.chat.completions.create.return_value = [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="hello"))],
                usage=None,
            ),
            SimpleNamespace(
                choices=[],
                usage=SimpleNamespace(
                    prompt_tokens=12, completion_tokens=8, total_tokens=20
                ),
            ),
        ]
        with patch.object(llm, "OpenAI", return_value=client):
            result = llm.official_gpt_call("prompt", "gpt-test", user=self.user)
        self.assertEqual(result.getvalue(), "hello")
        self.assertEqual(AIUsage.objects.get().total_tokens, 20)
        self.assertEqual(
            client.chat.completions.create.call_args.kwargs["stream_options"],
            {"include_usage": True},
        )

    def test_completed_retries_are_all_measured(self):
        client = MagicMock()
        valid = '{"title":"test","scenes":[{"scene":"1","sentences":[{"image_description":"cat"}]}]}'
        client.chat.completions.create.side_effect = [
            [
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content=text))],
                    usage={"prompt_tokens": 5, "completion_tokens": 3},
                )
            ]
            for text in ['{"title":"test","scenes":[]}', valid]
        ]
        with patch.object(llm, "OpenAI", return_value=client):
            llm.get_reply("prompt", gpt_model="gpt-test", user=self.user)
        self.assertEqual(AIUsage.objects.count(), 2)

    def test_failed_gpt_request_does_not_invent_usage(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("upstream")
        with patch.object(llm, "OpenAI", return_value=client):

            with self.assertRaises(APIException):
                llm.official_gpt_call("prompt", user=self.user)
        self.assertFalse(AIUsage.objects.exists())

    def test_tts_measures_characters_without_inventing_tokens(self):
        client = MagicMock()
        with patch.object(tts_utils, "OpenAI", return_value=client):
            tts_utils.OpenAITTSProvider.generate("Hello κόσμε", "unused.wav", user=self.user)
        usage = AIUsage.objects.get()
        self.assertEqual(usage.characters, len("Hello κόσμε"))
        self.assertIsNone(usage.total_tokens)

    def test_image_usage_is_saved_even_when_local_file_write_fails(self):
        client = MagicMock()
        client.images.generate.return_value = SimpleNamespace(
            usage={"input_tokens": 30, "output_tokens": 70, "total_tokens": 100},
            data=[SimpleNamespace(b64_json="YQ==")],
        )
        with (
            patch.object(openai_images, "OpenAI", return_value=client),
            patch.object(openai_images.MediaAsset, "from_visual", side_effect=OSError),
        ):
            with self.assertRaises(OSError):
                openai_images.OpenAIImageProvider.generate(
                    "cat", "unused/", "", user=self.user
                )
        usage = AIUsage.objects.get()
        self.assertEqual(
            (usage.service, usage.images, usage.total_tokens), ("images", 1, 100)
        )
