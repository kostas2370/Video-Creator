"""Transcribe source audio into validated, ordered caption words."""

import math
from pathlib import Path

from openai import OpenAI

from apps.apikeysmanagement.models import ApiKeys, Provider
from apps.common.media import run_ffmpeg
from apps.videomanagement.services.usage import record_usage
from apps.videomanagement.utils.captions.timing import normalize_words


def transcribe_audio(source, user, duration, directory, *, api_key=None):
    audio = Path(directory, "speech.mp3")
    run_ffmpeg(
        [
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            "64k",
            str(audio),
        ],
        timeout=120,
    )
    return transcribe_prepared_audio(audio, user, duration, api_key=api_key)


def transcribe_prepared_audio(audio, user, duration, *, api_key=None):
    """Send an already prepared audio file without encoding it again."""
    audio = Path(audio)
    client = OpenAI(
        api_key=api_key or ApiKeys.key_for(user, Provider.OPENAI),
        timeout=180,
        max_retries=1,
    )
    with audio.open("rb") as file:
        result = client.audio.transcriptions.create(
            file=file,
            model="whisper-1",
            response_format="verbose_json",
            timestamp_granularities=["word"],
        )
    record_usage(user, "stt", Provider.OPENAI, "whisper-1", seconds=math.ceil(duration))
    return normalize_words(result.words, duration)
