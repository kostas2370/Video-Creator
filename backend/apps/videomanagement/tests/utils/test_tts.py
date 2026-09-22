"""No network and no files: every provider call is stubbed and writes go to a tmpdir."""

import base64
import os
import tempfile
from unittest.mock import MagicMock, mock_open, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import APIException

from ...utils import tts_utils
from ...utils.tts_utils import (
    ApiSyn,
    get_voices_from_60db,
    get_voices_from_labs,
    save,
    tts_from_60db,
    tts_from_eleven_labs,
    tts_from_open_api,
)


def wrote(path, data=b"RIFF"):
    def write(*args, **kwargs):
        with open(path, "wb") as f:
            f.write(data)

    return write


class SaveTests(SimpleTestCase):
    def test_returns_none_when_there_is_no_voice(self):
        # Narration off: make_scene_speech asks for no audio at all.
        self.assertIsNone(save(None, "hello", "out.wav"))

    def test_routes_to_the_provider_the_voice_names(self):
        syn = ApiSyn(provider="eleven_labs", path="a-voice-id")
        out = os.path.join(tempfile.mkdtemp(), "out.wav")

        with patch.object(
            tts_utils, "tts_from_eleven_labs", side_effect=wrote(out)
        ) as eleven:
            self.assertEqual(save(syn, "hello", out), out)

        eleven.assert_called_once_with("hello", out, "a-voice-id", user=None)

    def test_hands_back_nothing_when_the_provider_wrote_no_audio(self):
        # The eleven_labs and 60db calls swallow their own errors, so a failed
        # synthesis would otherwise leave a scene pointing at a file that is not there.
        syn = ApiSyn(provider="eleven_labs", path="a-voice-id")
        out = os.path.join(tempfile.mkdtemp(), "missing.wav")

        with patch.object(tts_utils, "tts_from_eleven_labs"):
            self.assertIsNone(save(syn, "hello", out))

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


class VoiceListingTests(SimpleTestCase):
    @override_settings(XI_API_KEY="key")
    def test_reads_the_voices_out_of_the_eleven_labs_payload(self):
        response = MagicMock()
        response.json.return_value = {"voices": [{"voice_id": "abc"}]}

        with patch.object(tts_utils.requests, "get", return_value=response) as get:
            self.assertEqual(get_voices_from_labs(), [{"voice_id": "abc"}])

        self.assertEqual(get.call_args.kwargs["headers"]["xi-api-key"], "key")

    @override_settings(SIXTYDB_API_KEY="key")
    def test_reads_the_voices_out_of_the_60db_payload(self):
        response = MagicMock()
        response.json.return_value = {"data": [{"voice_id": "abc"}]}

        with patch.object(tts_utils.requests, "get", return_value=response) as get:
            self.assertEqual(get_voices_from_60db(), [{"voice_id": "abc"}])

        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "Bearer key")
