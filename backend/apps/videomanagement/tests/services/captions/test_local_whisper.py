import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from django.test import SimpleTestCase, override_settings

from apps.videomanagement.services.captions import transcription
from apps.videomanagement.services.captions.local_whisper import TranscriptionError


@override_settings(
    SPEECH_TRANSCRIPTION_PROVIDER="local",
    LOCAL_WHISPER_URL="http://whisper:9000",
    LOCAL_WHISPER_TIMEOUT=123,
)
class LocalWhisperTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.audio = Path(directory.name, "speech.mp3")
        self.audio.write_bytes(b"prepared audio")

    def response(self, words):
        return io.BytesIO(json.dumps({"words": words}).encode())

    def test_default_local_provider_preserves_word_timing_without_keys_or_paid_usage(
        self,
    ):
        with (
            patch(
                "apps.videomanagement.services.captions.local_whisper.urlopen",
                return_value=self.response(
                    [
                        {"word": " Hello", "start": 0.2, "end": 0.8},
                        {"word": "world", "start": 0.8, "end": 2.5},
                    ]
                ),
            ) as send,
            patch.object(transcription, "OpenAI") as client,
            patch.object(transcription.ApiKeys, "key_for") as key,
            patch.object(transcription, "record_usage") as usage,
            patch.object(transcription, "run_ffmpeg") as encode,
        ):
            words = transcription.transcribe_prepared_audio(self.audio, object(), 2)
        self.assertEqual(
            words,
            [
                {"text": "Hello", "start": 0.2, "end": 0.8},
                {"text": "world", "start": 0.8, "end": 2},
            ],
        )
        self.assertEqual(send.call_args.args[0].data, b"prepared audio")
        self.assertEqual(
            send.call_args.args[0].full_url, "http://whisper:9000/transcribe"
        )
        self.assertEqual(send.call_args.kwargs["timeout"], 123)
        client.assert_not_called()
        key.assert_not_called()
        usage.assert_not_called()
        encode.assert_not_called()

    def test_unavailable_service_has_actionable_error_and_no_paid_fallback(self):
        with (
            patch(
                "apps.videomanagement.services.captions.local_whisper.urlopen",
                side_effect=URLError("unreachable"),
            ),
            patch.object(transcription, "OpenAI") as client,
        ):
            with self.assertRaisesMessage(TranscriptionError, "whisper Docker service"):
                transcription.transcribe_prepared_audio(self.audio, object(), 2)
        client.assert_not_called()

    def test_rejects_malformed_local_words_and_handles_silence(self):
        for words in (None, [{"text": "missing timing"}], [None]):
            with (
                self.subTest(words=words),
                patch(
                    "apps.videomanagement.services.captions.local_whisper.urlopen",
                    return_value=self.response(words),
                ),
            ):
                with self.assertRaises(TranscriptionError):
                    transcription.transcribe_prepared_audio(self.audio, object(), 2)
        with patch(
            "apps.videomanagement.services.captions.local_whisper.urlopen",
            return_value=self.response([]),
        ):
            self.assertEqual(
                transcription.transcribe_prepared_audio(self.audio, object(), 2), []
            )

    @override_settings(SPEECH_TRANSCRIPTION_PROVIDER="invalid")
    def test_invalid_configuration_does_not_send_audio(self):
        with patch(
            "apps.videomanagement.services.captions.local_whisper.urlopen"
        ) as send:
            with self.assertRaisesMessage(TranscriptionError, "Choose local or openai"):
                transcription.transcribe_prepared_audio(self.audio, object(), 2)
        send.assert_not_called()
