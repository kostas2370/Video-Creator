import io
import json
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.videomanagement.integrations.llm import get_reply


class SeriesMemoryResponseTests(SimpleTestCase):
    def test_missing_or_malformed_episode_memory_is_retried_with_feedback(self):
        base = {
            "title": "Milo",
            "scenes": [
                {
                    "scene": "Discovery",
                    "sentences": [{"image_description": "Milo finds a lamp"}],
                }
            ],
        }
        for invalid in (None, {}, "", "x" * 801):
            with (
                self.subTest(invalid=type(invalid).__name__),
                patch(
                    "apps.videomanagement.integrations.llm.official_gpt_call",
                    side_effect=[
                        io.StringIO(json.dumps({**base, "episode_summary": invalid})),
                        io.StringIO(
                            json.dumps(
                                {**base, "episode_summary": "Milo found a lamp."}
                            )
                        ),
                    ],
                ) as call,
            ):
                result = get_reply(
                    "Draft an episode",
                    gpt_model="gpt-5",
                    narration=False,
                    require_episode_summary=True,
                )
                self.assertEqual(result["episode_summary"], "Milo found a lamp.")
                self.assertEqual(call.call_count, 2)
                self.assertIn("episode_summary", call.call_args.args[0])
