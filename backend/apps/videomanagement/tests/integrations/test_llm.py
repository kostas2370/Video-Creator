"""Every call out to a model provider is stubbed — no test here reaches the network."""

import io
import json
import base64
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import APIException

from apps.videomanagement.integrations import llm as llm
from apps.videomanagement.integrations.llm import (
    script_errors,
    claude_call,
    gemini_call,
    get_reply,
    get_update_sentence,
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
    def test_caps_every_model_with_a_reasoning_allowance_on_top(self):
        for model in ("gpt-4-turbo", "gpt-3.5-turbo", "gpt-5", "o3-mini"):
            with self.subTest(model=model):
                self.assertEqual(
                    token_limit_kwarg(model), {"max_completion_tokens": 1500}
                )


def a_reply(*scenes):
    return {"title": "t", "scenes": list(scenes)}


def a_scene(*sentences):
    return {"scene": "one", "sentences": list(sentences)}


A_SENTENCE = {"sentence": "hello", "image_description": "a cat"}


class ScriptErrorsTests(SimpleTestCase):
    def test_accepts_a_reply_with_the_shape_the_pipeline_walks(self):
        self.assertFalse(script_errors(a_reply(a_scene(A_SENTENCE))))

    def test_continuity_is_optional_for_old_scripts_but_validated_when_present(self):
        data = a_reply(a_scene(A_SENTENCE))
        self.assertFalse(script_errors(data))
        self.assertTrue(script_errors(data, require_visual_continuity=True))
        for invalid in (None, [], "x" * 3001):
            self.assertTrue(script_errors({**data, "visual_continuity": invalid}))
        self.assertFalse(script_errors({**data, "visual_continuity": ""}, require_visual_continuity=True))

    def test_rejects_a_reply_with_no_scenes_key(self):
        self.assertTrue(script_errors({"title": "t"}))

    def test_rejects_a_reply_with_no_title(self):
        self.assertTrue(script_errors({"scenes": [{"scene": "one"}]}))

    def test_rejects_an_empty_scene_list(self):
        self.assertTrue(script_errors({"title": "t", "scenes": []}))

    def test_rejects_scenes_that_are_not_labelled(self):
        self.assertTrue(script_errors({"title": "t", "scenes": [{"sentences": []}]}))

    def test_rejects_a_scene_with_no_sentences(self):
        self.assertTrue(script_errors(a_reply({"scene": "one"})))
        self.assertTrue(script_errors(a_reply(a_scene())))

    def test_rejects_a_sentence_with_nothing_to_illustrate(self):
        self.assertTrue(script_errors(a_reply(a_scene({"sentence": "hello"}))))

    def test_rejects_a_later_scene_that_is_malformed(self):
        self.assertTrue(
            script_errors(a_reply(a_scene(A_SENTENCE), {"scene": "two", "sentences": []}))
        )

    def test_rejects_invalid_types_and_empty_values(self):
        for value in (None, [], {"title": "t", "scenes": "oops"},
                      a_reply(None), a_reply(a_scene(None)),
                      a_reply(a_scene({"image_description": " "})),
                      a_reply(a_scene({"image_description": 1}))):
            with self.subTest(value=value):
                self.assertTrue(script_errors(value))

    def test_validates_requested_narration_and_scene_count(self):
        silent = a_reply(a_scene({"image_description": "cat"}))
        spoken = a_reply(a_scene(A_SENTENCE))
        self.assertFalse(script_errors(silent, narration=False, scene_count=1))
        self.assertTrue(script_errors(silent, narration=True))
        self.assertTrue(script_errors(spoken, narration=False))
        self.assertTrue(script_errors(spoken, scene_count=2))
        self.assertTrue(script_errors(a_reply(a_scene(A_SENTENCE, A_SENTENCE)), scene_count=1))


class OfficialGptCallTests(SimpleTestCase):
    @override_settings(OPEN_API_KEY="key", MAX_TOKENS=100, DEFAULT_GPT_MODEL="gpt-4")
    def test_joins_the_streamed_deltas(self):
        client = MagicMock()
        client.chat.completions.create.return_value = a_stream("he", "llo", None)

        with patch.object(llm, "OpenAI", return_value=client):
            self.assertEqual(official_gpt_call("a prompt").getvalue(), "hello")

    @override_settings(OPEN_API_KEY="key", MAX_TOKENS=100, DEFAULT_GPT_MODEL="gpt-4")
    def test_sends_the_token_cap_under_the_name_the_model_accepts(self):
        client = MagicMock()
        client.chat.completions.create.return_value = a_stream("hi")

        with patch.object(llm, "OpenAI", return_value=client):
            official_gpt_call("a prompt", gpt_model="gpt-5")

        self.assertIn(
            "max_completion_tokens", client.chat.completions.create.call_args.kwargs
        )

    @override_settings(OPEN_API_KEY="key", MAX_TOKENS=100, DEFAULT_GPT_MODEL="gpt-4")
    def test_falls_back_to_the_configured_model_when_none_was_asked_for(self):
        client = MagicMock()
        client.chat.completions.create.return_value = a_stream("hi")

        with patch.object(llm, "OpenAI", return_value=client):
            official_gpt_call("a prompt")

        self.assertEqual(
            client.chat.completions.create.call_args.kwargs["model"], "gpt-4"
        )

    @override_settings(OPEN_API_KEY="key", MAX_TOKENS=100, DEFAULT_GPT_MODEL="gpt-4")
    def test_sends_reference_image_as_a_chat_image_part(self):
        client = MagicMock()
        client.chat.completions.create.return_value = a_stream("hello")
        with patch.object(llm, "OpenAI", return_value=client):
            official_gpt_call("describe visible details", image="encoded-jpeg")
        content = client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
        self.assertEqual(content[0], {"type": "text", "text": "describe visible details"})
        self.assertEqual(content[1]["image_url"]["url"], "data:image/jpeg;base64,encoded-jpeg")

    def test_image_failure_has_clear_guidance_without_exposing_payload(self):
        with patch.object(llm, "OpenAI", side_effect=RuntimeError("private-image-data")):
            with self.assertRaisesRegex(APIException, "model that accepts images") as caught:
                official_gpt_call("prompt", image="encoded-jpeg")
        self.assertNotIn("private-image-data", str(caught.exception))

    def test_turns_a_provider_failure_into_an_api_exception(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("upstream is down")

        with patch.object(llm, "OpenAI", return_value=client):
            with self.assertRaises(APIException):
                official_gpt_call("a prompt")


class ClaudeCallTests(SimpleTestCase):
    def test_reads_text_after_thinking_blocks_without_sending_unsupported_temperature(self):
        client = MagicMock()
        client.messages.create.return_value.content = [MagicMock(type="thinking"), MagicMock(type="text", text="hello")]
        with patch.object(llm.anthropic, "Anthropic", return_value=client):
            self.assertEqual(claude_call("prompt").getvalue(), "hello")
        self.assertEqual(client.messages.create.call_args.kwargs["model"], "claude-sonnet-5-5")
        self.assertNotIn("temperature", client.messages.create.call_args.kwargs)

    def test_sends_reference_image_using_claude_base64_blocks(self):
        client = MagicMock()
        client.messages.create.return_value.content = [MagicMock(type="text", text="hello")]
        with patch.object(llm.anthropic, "Anthropic", return_value=client):
            claude_call("prompt", image="encoded-jpeg")
        content = client.messages.create.call_args.kwargs["messages"][0]["content"]
        self.assertEqual(content[0]["source"], {
            "type": "base64", "media_type": "image/jpeg", "data": "encoded-jpeg",
        })
        self.assertEqual(content[1], {"type": "text", "text": "prompt"})

    @override_settings(ANTHROPIC_API_KEY="key")
    def test_returns_the_message_text(self):
        client = MagicMock()
        client.messages.create.return_value.content = [MagicMock(type="text", text="hello")]

        with patch.object(llm.anthropic, "Anthropic", return_value=client):
            self.assertEqual(claude_call("a prompt").getvalue(), "hello")

    @override_settings(ANTHROPIC_API_KEY="key")
    def test_turns_a_provider_failure_into_an_api_exception(self):
        with patch.object(
            llm.anthropic, "Anthropic", side_effect=RuntimeError("no key")
        ):
            with self.assertRaises(APIException):
                claude_call("a prompt")


class GeminiCallTests(SimpleTestCase):
    def response(self, parts=None):
        response = MagicMock()
        response.json.return_value = {
            "candidates": [{"content": {"parts": parts or [{"text": "hello"}]}}],
            "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 3, "thoughtsTokenCount": 2},
        }
        return response

    @override_settings(GEMINI_API_KEY="key")
    def test_sends_the_current_model_and_reference_with_an_account_scoped_key(self):
        image = base64.b64encode(b"jpeg-bytes").decode()
        with patch.object(llm.requests, "post", return_value=self.response()) as post:
            self.assertEqual(gemini_call("prompt", image=image).getvalue(), "hello")
        self.assertTrue(post.call_args.args[0].endswith("models/gemini-3.8-flash:generateContent"))
        self.assertEqual(post.call_args.kwargs["headers"], {"x-goog-api-key": "key"})
        self.assertEqual(post.call_args.kwargs["json"]["contents"][0]["parts"], [
            {"text": "prompt"}, {"inlineData": {"mimeType": "image/jpeg", "data": image}},
        ])

    def test_ignores_thought_parts_and_records_all_reported_usage(self):
        response = self.response([{"text": "private reasoning", "thought": True}, {"text": "hello"}])
        with patch.object(llm.requests, "post", return_value=response), patch.object(llm, "record_usage") as record:
            self.assertEqual(gemini_call("prompt").getvalue(), "hello")
        self.assertEqual(record.call_args.args[4]["thoughtsTokenCount"], 2)

    def test_turns_a_provider_failure_into_an_api_exception(self):
        with patch.object(llm.requests, "post", side_effect=RuntimeError("upstream down")):
            with self.assertRaises(APIException):
                gemini_call("a prompt")

    def test_rejects_an_empty_or_blocked_response(self):
        response = self.response()
        response.json.return_value = {"promptFeedback": {"blockReason": "SAFETY"}}
        with patch.object(llm.requests, "post", return_value=response):
            with self.assertRaises(APIException):
                gemini_call("a prompt")


class GetReplyRoutingTests(SimpleTestCase):
    """Which provider a model name is sent to."""

    def route(self, gpt_model):
        with (
            patch.object(
                llm, "official_gpt_call", return_value=io.StringIO(A_SCRIPT)
            ) as openai,
            patch.object(
                llm, "claude_call", return_value=io.StringIO(A_SCRIPT)
            ) as claude,
            patch.object(
                llm, "gemini_call", return_value=io.StringIO(A_SCRIPT)
            ) as gemini,
        ):
            get_reply("a prompt", gpt_model=gpt_model)

        return {
            "openai": openai.called,
            "claude": claude.called,
            "gemini": gemini.called,
        }

    def test_omitted_model_uses_configured_default_and_matching_provider(self):
        for model, provider in (("gpt-5.4-mini", "official_gpt_call"),
                                ("claude-test", "claude_call"),
                                ("gemini-test", "gemini_call")):
            with self.subTest(model=model), override_settings(DEFAULT_GPT_MODEL=model):
                with patch.object(llm, provider, return_value=io.StringIO(A_SCRIPT)) as call:
                    get_reply("a prompt")
                call.assert_called_once_with("a prompt", model, user=None)

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
        with patch.object(llm, "official_gpt_call", side_effect=streams) as call:
            result = get_reply("a prompt", gpt_model="gpt-4", **kwargs)

        return result, call

    def test_retries_keep_the_image_and_encode_it_only_once(self):
        with patch.object(llm, "image_data", return_value="encoded-jpeg") as encode:
            parsed, call = self.reply('{"title":"incomplete"}', A_SCRIPT, reference_image="local-reference.png")
        self.assertEqual(parsed["title"], "Cats")
        encode.assert_called_once_with("local-reference.png")
        self.assertEqual([item.kwargs["image"] for item in call.call_args_list], ["encoded-jpeg", "encoded-jpeg"])

    def test_missing_reference_fails_before_any_model_request(self):
        with patch.object(llm, "official_gpt_call") as call, self.assertRaisesRegex(APIException, "could not be read"):
            get_reply("prompt", reference_image="/missing/reference.png")
        call.assert_not_called()

    def test_missing_ai_continuity_is_retried_in_the_same_storyboard_flow(self):
        corrected = json.dumps({**json.loads(A_SCRIPT), "visual_continuity": "Orange cat, green scarf."})
        parsed, call = self.reply(A_SCRIPT, corrected, require_visual_continuity=True)
        self.assertEqual(parsed["visual_continuity"], "Orange cat, green scarf.")
        self.assertEqual(call.call_count, 2)
        self.assertIn("visual_continuity", call.call_args.args[0])

    def test_empty_continuity_is_valid_when_no_shared_subject_is_needed(self):
        payload = json.dumps({**json.loads(A_SCRIPT), "visual_continuity": ""})
        parsed, call = self.reply(payload, require_visual_continuity=True)
        self.assertEqual(parsed["visual_continuity"], "")
        self.assertEqual(call.call_count, 1)

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

        self.assertIn("after 5 attempts", str(caught.exception))

    def test_retries_non_json_with_correction_feedback(self):
        parsed, call = self.reply("Not JSON", A_SCRIPT)
        self.assertEqual(parsed["title"], "Cats")
        self.assertIn("syntactically valid JSON", call.call_args.args[0])

    def test_retry_explains_count_and_narration_errors(self):
        import json
        fixed = json.loads(A_SCRIPT)
        fixed["scenes"] *= 2
        parsed, call = self.reply(A_SCRIPT, json.dumps(fixed), scene_count=2, narration=True)
        self.assertEqual(len(parsed["scenes"]), 2)
        self.assertIn("exactly 2 scenes", call.call_args.args[0])

    def test_returns_the_raw_stream_when_no_json_was_asked_for(self):
        stream = io.StringIO("just words")
        with patch.object(llm, "official_gpt_call", return_value=stream):
            result = get_reply("a prompt", reply_format="text", gpt_model="gpt-4")

        self.assertIs(result, stream)


class GetUpdateSentenceTests(SimpleTestCase):
    def test_joins_the_streamed_rewrite(self):
        with patch.object(llm, "get_reply", return_value=io.StringIO("a rewrite")):
            self.assertEqual(get_update_sentence("a prompt"), "a rewrite")


class SelectFromVisionTests(SimpleTestCase):
    def answer(self, text):
        client = MagicMock()
        client.chat.completions.create.return_value.choices[0].message.content = text

        with patch.object(llm, "OpenAI", return_value=client):
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

    def test_rejects_ambiguous_or_out_of_range_selections(self):
        for answer in ("", "12", "0", "4", "Image 2", "1 or 3"):
            with self.subTest(answer=answer), self.assertRaises(APIException):
                self.answer(answer)

    def test_candidate_count_is_dynamic(self):
        client = MagicMock()
        client.chat.completions.create.return_value.choices[0].message.content = "2"
        with patch.object(llm, "OpenAI", return_value=client):
            self.assertEqual(select_from_vision("cat", ["a", "b"]), 1)
        content = client.chat.completions.create.call_args.kwargs["messages"][0]["content"][0]["text"]
        self.assertIn("these 2 images", content)
        self.assertIn("1 to 2", content)

    def test_rejects_empty_candidate_list_without_calling_provider(self):
        with patch.object(llm, "OpenAI") as client, self.assertRaises(ValueError):
            select_from_vision("cat", [])
        client.assert_not_called()
