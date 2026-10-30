import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.videomanagement.services.captions import transcription


class PreparedTranscriptionTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.audio = self.directory / "part-0.mp3"
        self.audio.write_bytes(b"prepared audio")
        self.owner = object()
        self.client = self.enterContext(patch.object(transcription, "OpenAI"))
        self.usage = self.enterContext(patch.object(transcription, "record_usage"))
        self.encode = self.enterContext(patch.object(transcription, "run_ffmpeg"))
        self.create = self.client.return_value.audio.transcriptions.create
        self.create.return_value = SimpleNamespace(
            words=[SimpleNamespace(word="Hello", start=0.1, end=0.5)]
        )

    def test_prepared_audio_is_sent_directly_without_encoding(self):
        def create(**kwargs):
            self.assertEqual(kwargs["file"].read(), b"prepared audio")
            self.assertEqual(Path(kwargs["file"].name), self.audio)
            self.assertEqual(kwargs["model"], "whisper-1")
            self.assertEqual(kwargs["timestamp_granularities"], ["word"])
            return self.create.return_value

        self.create.side_effect = create
        words = transcription.transcribe_prepared_audio(
            self.audio, self.owner, 2.1, api_key="test-key"
        )
        self.encode.assert_not_called()
        self.assertEqual(words, [{"text": "Hello", "start": 0.1, "end": 0.5}])
        self.client.assert_called_once_with(
            api_key="test-key", timeout=180, max_retries=1
        )
        self.usage.assert_called_once_with(
            self.owner, "stt", "OPENAI", "whisper-1", seconds=3
        )
        self.assertTrue(self.create.call_args.kwargs["file"].closed)

    def test_normal_source_is_still_encoded_before_transcription(self):
        def encode(arguments, **kwargs):
            Path(arguments[-1]).write_bytes(b"encoded audio")

        def create(**kwargs):
            self.assertEqual(kwargs["file"].read(), b"encoded audio")
            return self.create.return_value

        self.encode.side_effect = encode
        self.create.side_effect = create
        transcription.transcribe_audio(
            self.audio, self.owner, 2, self.directory, api_key="test-key"
        )
        self.encode.assert_called_once()
        self.create.assert_called_once()

    def test_provider_failure_closes_the_file_and_does_not_record_usage(self):
        self.create.side_effect = RuntimeError("provider unavailable")
        with self.assertRaisesMessage(RuntimeError, "provider unavailable"):
            transcription.transcribe_prepared_audio(
                self.audio, self.owner, 2, api_key="test-key"
            )
        self.assertTrue(self.create.call_args.kwargs["file"].closed)
        self.usage.assert_not_called()
        self.encode.assert_not_called()
