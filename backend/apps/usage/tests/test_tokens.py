from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.usage.tokens import (
    TOKEN_USAGE_ADAPTERS,
    TokenUsageAdapter,
    normalize_token_usage,
)


class TokenUsageTests(SimpleTestCase):
    def test_common_formats_work_without_provider_specific_branching(self):
        for payload in (
            {"input_tokens": 12, "output_tokens": 8},
            {"prompt_tokens": 12, "completion_tokens": 8},
            {"prompt_token_count": 12, "candidates_token_count": 8},
        ):
            for usage in (payload, SimpleNamespace(**payload)):
                with self.subTest(usage=usage):
                    self.assertEqual(
                        normalize_token_usage(usage),
                        {
                            "input_tokens": 12,
                            "output_tokens": 8,
                            "total_tokens": 20,
                        },
                    )

    def test_preserves_reported_total_even_when_components_differ(self):
        result = normalize_token_usage(
            {
                "prompt_token_count": 3,
                "candidates_token_count": 4,
                "total_token_count": 9,
            }
        )
        self.assertEqual(result["total_tokens"], 9)

    def test_zero_counts_are_valid_and_take_precedence_over_aliases(self):
        result = normalize_token_usage(
            {
                "input_tokens": 0,
                "prompt_tokens": 99,
                "output_tokens": 0,
                "total_tokens": 0,
            }
        )
        self.assertEqual(list(result.values()), [0, 0, 0])

    def test_missing_or_invalid_components_do_not_invent_totals(self):
        for value in (None, -1, True, "12", 1.5):
            with self.subTest(value=value):
                result = normalize_token_usage(
                    {"input_tokens": value, "output_tokens": 4}
                )
                self.assertIsNone(result["input_tokens"])
                self.assertIsNone(result["total_tokens"])
        self.assertEqual(
            normalize_token_usage(None),
            {
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
            },
        )

    def test_cache_tokens_are_added_only_by_the_selected_adapter(self):
        payload = {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_read_input_tokens": 7,
            "cache_creation_input_tokens": 3,
        }
        self.assertEqual(
            normalize_token_usage(payload, "ANTHROPIC")["total_tokens"], 25
        )
        self.assertEqual(normalize_token_usage(payload, "OPENAI")["total_tokens"], 15)
        self.assertEqual(normalize_token_usage(payload, "custom")["total_tokens"], 15)

    def test_a_new_provider_can_define_its_format_without_changing_the_recorder(self):
        adapter = TokenUsageAdapter(
            input_fields=("received",),
            output_fields=("generated",),
            total_fields=("used",),
        )
        with patch.dict(TOKEN_USAGE_ADAPTERS, {"new-provider": adapter}):
            self.assertEqual(
                normalize_token_usage({"received": 10, "generated": 3}, "new-provider"),
                {
                    "input_tokens": 10,
                    "output_tokens": 3,
                    "total_tokens": 13,
                },
            )
