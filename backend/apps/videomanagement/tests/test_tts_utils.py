"""No network and no files: every provider call is stubbed and writes go to a tmpdir."""

import base64
import os
import tempfile
from unittest.mock import MagicMock, mock_open, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import APIException

from ..utils import tts_utils
from ..utils.tts_utils import (
    ApiSyn,
    save,
    tts_from_60db,
    tts_from_eleven_labs,
    tts_from_open_api,
)


class SaveTests(SimpleTestCase):
    def test_returns_none_when_there_is_no_voice(self):
        # Narration off: make_scene_speech asks for no audio at all.
        self.assertIsNone(save(None, "hello", "out.wav"))

    def test_routes_to_the_provider_the_voice_names(self):
        syn = ApiSyn(provider="eleven_labs", path="a-voice-id")

        with patch.object(tts_utils, "tts_from_eleven_labs") as eleven:
            self.assertEqual(save(syn, "hello", "out.wav"), "out.wav")

        eleven.assert_called_once_with("hello", "out.wav", "a-voice-id", user=None)

    def test_routes_each_supported_provider_to_its_own_function(self):
        for provider, function in (
            ("open_ai", "tts_from_open_api"),
            ("eleven_labs", "tts_from_eleven_labs"),
            ("60db", "tts_from_60db"),
        ):
            with self.subTest(provider=provider):
                with patch.object(tts_utils, function) as call:
                    save(ApiSyn(provider=provider, path="v"), "hello", "out.wav")

                call.assert_called_once()

    def test_rejects_a_voice_whose_provider_is_not_supported(self):
        syn = ApiSyn(provider="a-local-model", path="/models/x")

        with self.assertRaises(APIException):
            save(syn, "hello", "out.wav")


class OpenAiTtsTests(SimpleTestCase):
    @override_settings(OPEN_API_KEY="key")
    def test_asks_for_wav_because_the_pipeline_writes_a_wav_path(self):
        client = MagicMock()

        with patch.object(tts_utils, "OpenAI", return_value=client):
            tts_from_open_api("hello", "out.wav", voice="onyx")

        kwargs = client.audio.speech.create.call_args.kwargs
        self.assertEqual(kwargs["response_format"], "wav")
        self.assertEqual(kwargs["voice"], "onyx")
        client.audio.speech.create.return_value.stream_to_file.assert_called_once_with(
            "out.wav"
        )


class ElevenLabsTtsTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = os.path.join(self.tmp.name, "out.wav")

    @override_settings(XI_API_KEY="key")
    def test_streams_the_response_body_to_disk(self):
        response = MagicMock()
        response.iter_content.return_value = [b"RIFF", b"", b"data"]

        with patch.object(tts_utils.requests, "post", return_value=response) as post:
            tts_from_eleven_labs("hello", self.out, "a-voice-id")

        self.assertEqual(open(self.out, "rb").read(), b"RIFFdata")
        self.assertIn("a-voice-id", post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs["headers"]["xi-api-key"], "key")

    @override_settings(XI_API_KEY="key")
    def test_swallows_a_provider_failure_rather_than_failing_generation(self):
        response = MagicMock()
        response.raise_for_status.side_effect = RuntimeError("429")

        with patch.object(tts_utils.requests, "post", return_value=response):
            self.assertIs(tts_from_eleven_labs("hello", self.out, "v"), response)

        self.assertFalse(os.path.exists(self.out))


class SixtyDbTtsTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = os.path.join(self.tmp.name, "out.wav")

    @override_settings(SIXTYDB_API_KEY="key")
    def test_decodes_the_base64_payload_to_disk(self):
        # Unlike Eleven Labs, 60db answers with JSON carrying the audio as base64.
        response = MagicMock()
        response.json.return_value = {
            "audio_base64": base64.b64encode(b"RIFFdata").decode()
        }

        with patch.object(tts_utils.requests, "post", return_value=response) as post:
            tts_from_60db("hello", self.out, "a-voice-id")

        self.assertEqual(open(self.out, "rb").read(), b"RIFFdata")
        self.assertEqual(post.call_args.kwargs["json"]["voice_id"], "a-voice-id")
        self.assertEqual(post.call_args.kwargs["json"]["output_format"], "wav")

    @override_settings(SIXTYDB_API_KEY="key")
    def test_writes_nothing_when_the_payload_carries_no_audio(self):
        response = MagicMock()
        response.json.return_value = {"message": "out of credits"}

        with patch.object(tts_utils.requests, "post", return_value=response):
            with patch("builtins.open", mock_open()) as opened:
                tts_from_60db("hello", self.out, "v")

        opened.assert_not_called()

    @override_settings(SIXTYDB_API_KEY="key")
    def test_swallows_a_provider_failure_rather_than_failing_generation(self):
        response = MagicMock()
        response.raise_for_status.side_effect = RuntimeError("500")

        with patch.object(tts_utils.requests, "post", return_value=response):
            self.assertIs(tts_from_60db("hello", self.out, "v"), response)

        self.assertFalse(os.path.exists(self.out))
