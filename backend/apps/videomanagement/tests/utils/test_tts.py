from apps.apikeysmanagement.models import Provider

import base64
import os
import tempfile
from unittest.mock import MagicMock, mock_open, patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import APIException

from apps.usermanagement.baker_recipes import user as user_recipe
from ...utils import tts_utils
from ...utils.tts_utils import (
    ApiSyn,
    get_voices_from_sixtydb,
    get_voices_from_elevenlabs,
    save,
    tts_from_sixtydb,
    tts_from_elevenlabs,
    tts_from_openai,
)


def wrote(path, data=b"RIFF"):
    def write(*args, **kwargs):
        with open(path, "wb") as f:
            f.write(data)

    return write


class SaveTests(TestCase):
    def setUp(self):
        self.user = user_recipe.make()

    def test_returns_none_when_there_is_no_voice(self):
        self.assertIsNone(save(None, "hello", "out.wav", user=self.user))

    def test_routes_to_the_provider_the_voice_names(self):
        syn = ApiSyn(provider=Provider.ELEVENLABS, path="a-voice-id")
        out = os.path.join(tempfile.mkdtemp(), "out.wav")

        with patch.object(
            tts_utils, "tts_from_elevenlabs", side_effect=wrote(out)
        ) as eleven:
            self.assertEqual(save(syn, "hello", out, user=self.user), out)

        eleven.assert_called_once_with(
            "hello",
            out,
            "a-voice-id",
            user=self.user,
            provider_name=Provider.ELEVENLABS,
        )

    def test_hands_back_nothing_when_the_provider_wrote_no_audio(self):
        syn = ApiSyn(provider=Provider.ELEVENLABS, path="a-voice-id")
        out = os.path.join(tempfile.mkdtemp(), "missing.wav")

        with patch.object(tts_utils, "tts_from_elevenlabs"):
            self.assertIsNone(save(syn, "hello", out, user=self.user))

    def test_routes_each_supported_provider_to_its_own_function(self):
        for provider, function in (
            (Provider.OPENAI, "tts_from_openai"),
            (Provider.ELEVENLABS, "tts_from_elevenlabs"),
            (Provider.SIXTYDB, "tts_from_sixtydb"),
        ):
            with self.subTest(provider=provider):
                with patch.object(tts_utils, function) as call:
                    save(
                        ApiSyn(provider=provider, path="v"),
                        "hello",
                        "out.wav",
                        user=self.user,
                    )

                call.assert_called_once()

    def test_rejects_a_voice_whose_provider_is_not_supported(self):
        syn = ApiSyn(provider="a-local-model", path="/models/x")

        with self.assertRaises(APIException):
            save(syn, "hello", "out.wav", user=self.user)


class OpenAiTtsTests(TestCase):
    def setUp(self):
        self.user = user_recipe.make()

    @override_settings(OPEN_API_KEY="key")
    def test_asks_for_wav_because_the_pipeline_writes_a_wav_path(self):
        client = MagicMock()

        with patch.object(tts_utils, "OpenAI", return_value=client):
            tts_from_openai("hello", "out.wav", voice="onyx", user=self.user)

        kwargs = client.audio.speech.create.call_args.kwargs
        self.assertEqual(kwargs["response_format"], "wav")
        self.assertEqual(kwargs["voice"], "onyx")
        client.audio.speech.create.return_value.stream_to_file.assert_called_once_with(
            "out.wav"
        )


class ElevenLabsTtsTests(TestCase):
    def setUp(self):
        self.user = user_recipe.make()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = os.path.join(self.tmp.name, "out.wav")

    @override_settings(XI_API_KEY="key")
    def test_streams_the_response_body_to_disk(self):
        response = MagicMock()
        response.iter_content.return_value = [b"RIFF", b"", b"data"]

        with patch.object(tts_utils.requests, "post", return_value=response) as post:
            tts_from_elevenlabs("hello", self.out, "a-voice-id", user=self.user)

        self.assertEqual(open(self.out, "rb").read(), b"RIFFdata")
        self.assertIn("a-voice-id", post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs["headers"]["xi-api-key"], "key")

    @override_settings(XI_API_KEY="key")
    def test_swallows_a_provider_failure_rather_than_failing_generation(self):
        response = MagicMock()
        response.raise_for_status.side_effect = RuntimeError("429")

        with patch.object(tts_utils.requests, "post", return_value=response):
            self.assertIs(
                tts_from_elevenlabs("hello", self.out, "v", user=self.user), response
            )

        self.assertFalse(os.path.exists(self.out))


class SixtyDbTtsTests(TestCase):
    def setUp(self):
        self.user = user_recipe.make()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = os.path.join(self.tmp.name, "out.wav")

    @override_settings(SIXTYDB_API_KEY="key")
    def test_decodes_the_base64_payload_to_disk(self):
        response = MagicMock()
        response.json.return_value = {
            "audio_base64": base64.b64encode(b"RIFFdata").decode()
        }

        with patch.object(tts_utils.requests, "post", return_value=response) as post:
            tts_from_sixtydb("hello", self.out, "a-voice-id", user=self.user)

        self.assertEqual(open(self.out, "rb").read(), b"RIFFdata")
        self.assertEqual(post.call_args.kwargs["json"]["voice_id"], "a-voice-id")
        self.assertEqual(post.call_args.kwargs["json"]["output_format"], "wav")

    @override_settings(SIXTYDB_API_KEY="key")
    def test_writes_nothing_when_the_payload_carries_no_audio(self):
        response = MagicMock()
        response.json.return_value = {"message": "out of credits"}

        with patch.object(tts_utils.requests, "post", return_value=response):
            with patch("builtins.open", mock_open()) as opened:
                tts_from_sixtydb("hello", self.out, "v", user=self.user)

        opened.assert_not_called()

    @override_settings(SIXTYDB_API_KEY="key")
    def test_swallows_a_provider_failure_rather_than_failing_generation(self):
        response = MagicMock()
        response.raise_for_status.side_effect = RuntimeError("500")

        with patch.object(tts_utils.requests, "post", return_value=response):
            self.assertIs(
                tts_from_sixtydb("hello", self.out, "v", user=self.user), response
            )

        self.assertFalse(os.path.exists(self.out))


class VoiceListingTests(TestCase):
    def setUp(self):
        self.user = user_recipe.make()

    @override_settings(XI_API_KEY="key")
    def test_reads_the_voices_out_of_the_eleven_labs_payload(self):
        response = MagicMock()
        response.json.return_value = {"voices": [{"voice_id": "abc"}]}

        with patch.object(tts_utils.requests, "get", return_value=response) as get:
            self.assertEqual(
                get_voices_from_elevenlabs(user=self.user), [{"voice_id": "abc"}]
            )

        self.assertEqual(get.call_args.kwargs["headers"]["xi-api-key"], "key")

    @override_settings(SIXTYDB_API_KEY="key")
    def test_reads_the_voices_out_of_the_60db_payload(self):
        response = MagicMock()
        response.json.return_value = {"data": [{"voice_id": "abc"}]}

        with patch.object(tts_utils.requests, "get", return_value=response) as get:
            self.assertEqual(
                get_voices_from_sixtydb(user=self.user), [{"voice_id": "abc"}]
            )

        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "Bearer key")
