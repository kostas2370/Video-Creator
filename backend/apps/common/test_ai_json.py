from django.test import SimpleTestCase

from .ai_json import parse_ai_json


class AIJSONTests(SimpleTestCase):
    def test_reads_plain_fenced_and_prose_wrapped_objects(self):
        for raw in (
            '{"text": "Hello"}',
            '  {"text": "Hello"}  ',
            '```json\n{"text": "Hello"}\n```',
            '```JSON\n{"text": "Hello"}\n```',
            '```\n{"text": "Hello"}\n```',
            'Here is the result:\n{"text": "Hello"}\nDone.',
        ):
            with self.subTest(raw=raw):
                self.assertEqual(parse_ai_json(raw), {"text": "Hello"})

    def test_preserves_json_types_for_caller_validation(self):
        for raw, expected in (
            ('[{"text": "Hello"}]', [{"text": "Hello"}]),
            ("```json\n[1, 2]\n```", [1, 2]),
            ('"text"', "text"),
            ("null", None),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(parse_ai_json(raw), expected)

    def test_rejects_invalid_json_and_non_text_responses(self):
        for raw in (
            None,
            {},
            "",
            "not JSON",
            '{"text":}',
            '[{"text": "Hello"}',
            "{} {}",
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_ai_json(raw)
