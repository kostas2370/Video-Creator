import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.clips.processing import transcribe_part
from apps.videomanagement.services.captions import transcription


class ChunkEncodingTests(SimpleTestCase):
    def test_chunk_is_encoded_once_and_keeps_source_timestamps(self):
        project = SimpleNamespace(
            range_start=0, range_stop=1220, source=SimpleNamespace(path="source.mp4")
        )
        owner = object()

        def encode(arguments, **kwargs):
            Path(arguments[-1]).write_bytes(b"prepared chunk")

        def create(**kwargs):
            self.assertEqual(kwargs["file"].read(), b"prepared chunk")
            return SimpleNamespace(
                words=[SimpleNamespace(word="Hello", start=2.1, end=2.4)]
            )

        with (
            tempfile.TemporaryDirectory() as directory,
            patch("apps.clips.processing.close_old_connections"),
            patch("apps.clips.processing.connections.close_all"),
            patch("apps.clips.processing.run_ffmpeg", side_effect=encode) as prepare,
            patch.object(transcription, "run_ffmpeg") as reencode,
            patch.object(transcription.ApiKeys, "key_for", return_value="test-key"),
            patch.object(transcription, "OpenAI") as client,
            patch.object(transcription, "record_usage") as usage,
        ):
            client.return_value.audio.transcriptions.create.side_effect = create
            words = transcribe_part(project, 1, directory, owner)

        prepare.assert_called_once()
        reencode.assert_not_called()
        self.assertEqual(words, [{"text": "Hello", "start": 600.1, "end": 600.4}])
        usage.assert_called_once_with(owner, "stt", "OPENAI", "whisper-1", seconds=604)
