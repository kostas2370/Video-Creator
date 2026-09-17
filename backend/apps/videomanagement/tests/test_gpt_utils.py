"""Every call out to a model provider is stubbed — no test here reaches the network."""

import io
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import APIException

from ..utils import gpt_utils
from ..utils.gpt_utils import (
    check_json,
    claude_call,
    gemini_call,
    get_reply,
    get_update_sentence,
    get_voices_from_60db,
    get_voices_from_labs,
    official_gpt_call,
    select_from_vision,
    token_limit_kwarg,
)

A_SCRIPT = (
    '{"title": "Cats", "scenes": [{"scene": "one", "sentences": '
    '[{"sentence": "hello", "image_description": "a cat"}]}]}'
)


def a_stream(*contents):
    """An OpenAI streaming response yielding one delta per argument."""
    chunks = []
    for content in contents:
        chunk = MagicMock()
        chunk.choices[0].delta.content = content
        chunks.append(chunk)

    return chunks


class TokenLimitKwargTests(SimpleTestCase):
    @override_settings(MAX_TOKENS=1000, REASONING_TOKEN_ALLOWANCE=500)
    def test_uses_max_tokens_for_the_gpt_4_era(self):
        self.assertEqual(token_limit_kwarg("gpt-4-turbo"), {"max_tokens": 1000})
        self.assertEqual(token_limit_kwarg("gpt-3.5-turbo"), {"max_tokens": 1000})

    @override_settings(MAX_TOKENS=1000, REASONING_TOKEN_ALLOWANCE=500)
    def test_adds_a_reasoning_allowance_for_newer_models(self):
        # max_completion_tokens also covers reasoning tokens, so a model that thinks
        # for longer than MAX_TOKENS would otherwise return an empty message.
        self.assertEqual(token_limit_kwarg("gpt-5"), {"max_completion_tokens": 1500})
        self.assertEqual(token_limit_kwarg("o3-mini"), {"max_completion_tokens": 1500})


class CheckJsonTests(SimpleTestCase):
    def test_accepts_a_reply_with_the_shape_the_pipeline_walks(self):
        self.assertTrue(
            check_json({"title": "t", "scenes": [{"scene": "one", "sentences": []}]})
        )

    def test_rejects_a_reply_with_no_scenes_key(self):
        self.assertFalse(check_json({"title": "t"}))

    def test_rejects_a_reply_with_no_title(self):
        self.assertFalse(check_json({"scenes": [{"scene": "one"}]}))

    def test_rejects_an_empty_scene_list(self):
        self.assertFalse(check_json({"title": "t", "scenes": []}))

    def test_rejects_scenes_that_are_not_labelled(self):
        self.assertFalse(check_json({"title": "t", "scenes": [{"sentences": []}]}))


class OfficialGptCallTests(SimpleTestCase):
    @override_settings(OPEN_API_KEY="key", MAX_TOKENS=100, DEFAULT_GPT_MODEL="gpt-4")
    def test_joins_the_streamed_deltas(self):
        client = MagicMock()
        client.chat.completions.create.return_value = a_stream("he", "llo", None)

        with patch.object(gpt_utils, "OpenAI", return_value=client):
            self.assertEqual(official_gpt_call("a prompt").getvalue(), "hello")

    @override_settings(OPEN_API_KEY="key", MAX_TOKENS=100, DEFAULT_GPT_MODEL="gpt-4")
    def test_sends_the_token_cap_under_the_name_the_model_accepts(self):
        client = MagicMock()
        client.chat.completions.create.return_value = a_stream("hi")

        with patch.object(gpt_utils, "OpenAI", return_value=client):
            official_gpt_call("a prompt", gpt_model="gpt-5")

        self.assertIn(
            "max_completion_tokens", client.chat.completions.create.call_args.kwargs
        )

    @override_settings(OPEN_API_KEY="key", MAX_TOKENS=100, DEFAULT_GPT_MODEL="gpt-4")
    def test_falls_back_to_the_configured_model_when_none_was_asked_for(self):
        client = MagicMock()
        client.chat.completions.create.return_value = a_stream("hi")

        with patch.object(gpt_utils, "OpenAI", return_value=client):
            official_gpt_call("a prompt")

        self.assertEqual(
            client.chat.completions.create.call_args.kwargs["model"], "gpt-4"
        )

    @override_settings(OPEN_API_KEY="key", MAX_TOKENS=100, DEFAULT_GPT_MODEL="gpt-4")
    def test_turns_a_provider_failure_into_an_api_exception(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("upstream is down")

        with patch.object(gpt_utils, "OpenAI", return_value=client):
            with self.assertRaises(APIException):
                official_gpt_call("a prompt")


class ClaudeCallTests(SimpleTestCase):
    @override_settings(ANTHROPIC_API_KEY="key")
    def test_returns_the_message_text(self):
        client = MagicMock()
        client.messages.create.return_value.content = [MagicMock(text="hello")]

        with patch.object(gpt_utils.anthropic, "Anthropic", return_value=client):
            self.assertEqual(claude_call("a prompt").getvalue(), "hello")

    @override_settings(ANTHROPIC_API_KEY="key")
    def test_turns_a_provider_failure_into_an_api_exception(self):
        with patch.object(
            gpt_utils.anthropic, "Anthropic", side_effect=RuntimeError("no key")
        ):
            with self.assertRaises(APIException):
                claude_call("a prompt")


class GeminiCallTests(SimpleTestCase):
    @override_settings(GEMINI_API_KEY="key")
    def test_joins_the_streamed_chunks(self):
        model = MagicMock()
        model.generate_content.return_value = ["he", "llo"]

        with (
            patch.object(gpt_utils.genai, "configure"),
            patch.object(gpt_utils.genai, "GenerativeModel", return_value=model),
        ):
            self.assertEqual(gemini_call("a prompt").getvalue(), "hello")

    @override_settings(GEMINI_API_KEY="key")
    def test_turns_a_provider_failure_into_an_api_exception(self):
        with patch.object(
            gpt_utils.genai, "configure", side_effect=RuntimeError("no key")
        ):
            with self.assertRaises(APIException):
                gemini_call("a prompt")


class GetReplyRoutingTests(SimpleTestCase):
    """Which provider a model name is sent to."""

    def route(self, gpt_model):
        with (
            patch.object(
                gpt_utils, "official_gpt_call", return_value=io.StringIO(A_SCRIPT)
            ) as openai,
            patch.object(
                gpt_utils, "claude_call", return_value=io.StringIO(A_SCRIPT)
            ) as claude,
            patch.object(
                gpt_utils, "gemini_call", return_value=io.StringIO(A_SCRIPT)
            ) as gemini,
        ):
            get_reply("a prompt", gpt_model=gpt_model)

        return {
            "openai": openai.called,
            "claude": claude.called,
            "gemini": gemini.called,
        }

    def test_sends_gpt_and_the_o_series_to_openai(self):
        for model in ("gpt-4", "gpt-5.4", "o1", "o3-mini", "o4-mini"):
            with self.subTest(model=model):
                self.assertTrue(self.route(model)["openai"])

    def test_sends_claude_models_to_anthropic(self):
        self.assertTrue(self.route("claude-3-5-sonnet-20240620")["claude"])

    def test_sends_gemini_models_to_google(self):
        self.assertTrue(self.route("gemini-1.5-pro")["gemini"])

    @override_settings(DEFAULT_GPT_MODEL="gpt-4")
    def test_falls_back_to_openai_for_an_unknown_name(self):
        self.assertTrue(self.route("some-new-model")["openai"])

    @override_settings(DEFAULT_GPT_MODEL="gpt-4")
    def test_falls_back_to_openai_when_no_model_was_named(self):
        self.assertTrue(self.route(None)["openai"])


class GetReplyParsingTests(SimpleTestCase):
    def reply(self, *payloads, **kwargs):
        streams = [io.StringIO(payload) for payload in payloads]
        with patch.object(gpt_utils, "official_gpt_call", side_effect=streams) as call:
            result = get_reply("a prompt", gpt_model="gpt-4", **kwargs)

        return result, call

    def test_parses_the_script_out_of_the_reply(self):
        parsed, _ = self.reply(A_SCRIPT)

        self.assertEqual(parsed["title"], "Cats")

    def test_ignores_prose_the_model_wrapped_the_json_in(self):
        # Models keep adding a lead-in and a code fence despite being told not to.
        parsed, _ = self.reply(f"Sure! Here you go:\n```json\n{A_SCRIPT}\n```")

        self.assertEqual(parsed["title"], "Cats")

    def test_retries_a_reply_that_parses_but_has_the_wrong_shape(self):
        parsed, call = self.reply('{"title": "Cats"}', A_SCRIPT)

        self.assertEqual(parsed["title"], "Cats")
        self.assertEqual(call.call_count, 2)

    def test_gives_up_after_five_badly_shaped_replies(self):
        with self.assertRaises(Exception) as caught:
            self.reply(*['{"title": "Cats"}'] * 5)

        self.assertIn("Max gpt limit is 5", str(caught.exception))

    def test_raises_rather_than_retrying_when_the_reply_is_not_json_at_all(self):
        with self.assertRaises(APIException):
            self.reply("I cannot help with that.")

    def test_returns_the_raw_stream_when_no_json_was_asked_for(self):
        stream = io.StringIO("just words")
        with patch.object(gpt_utils, "official_gpt_call", return_value=stream):
            result = get_reply("a prompt", reply_format="text", gpt_model="gpt-4")

        self.assertIs(result, stream)


class GetUpdateSentenceTests(SimpleTestCase):
    def test_joins_the_streamed_rewrite(self):
        with patch.object(
            gpt_utils.g4f.ChatCompletion, "create", return_value=["a ", "rewrite"]
        ):
            self.assertEqual(get_update_sentence("a prompt"), "a rewrite")


class SelectFromVisionTests(SimpleTestCase):
    def answer(self, text):
        client = MagicMock()
        client.chat.completions.create.return_value.choices[0].message.content = text

        with patch.object(gpt_utils, "OpenAI", return_value=client):
            return select_from_vision("a cat", ["a.png", "b.png", "c.png"]), client

    @override_settings(OPEN_API_KEY="key")
    def test_turns_the_models_choice_into_a_zero_based_index(self):
        for answer, index in (("1", 0), ("2", 1), ("3", 2)):
            with self.subTest(answer=answer):
                self.assertEqual(self.answer(answer)[0], index)

    @override_settings(OPEN_API_KEY="key")
    def test_sends_every_image_alongside_the_question(self):
        _, client = self.answer("1")

        content = client.chat.completions.create.call_args.kwargs["messages"][0][
            "content"
        ]
        self.assertEqual([part["type"] for part in content[1:]], ["image_url"] * 3)


class VoiceListingTests(SimpleTestCase):
    @override_settings(XI_API_KEY="key")
    def test_reads_the_voices_out_of_the_eleven_labs_payload(self):
        response = MagicMock()
        response.json.return_value = {"voices": [{"voice_id": "abc"}]}

        with patch.object(gpt_utils.requests, "get", return_value=response) as get:
            self.assertEqual(get_voices_from_labs(), [{"voice_id": "abc"}])

        self.assertEqual(get.call_args.kwargs["headers"]["xi-api-key"], "key")

    @override_settings(SIXTYDB_API_KEY="key")
    def test_reads_the_voices_out_of_the_60db_payload(self):
        response = MagicMock()
        response.json.return_value = {"data": [{"voice_id": "abc"}]}

        with patch.object(gpt_utils.requests, "get", return_value=response) as get:
            self.assertEqual(get_voices_from_60db(), [{"voice_id": "abc"}])

        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "Bearer key")
