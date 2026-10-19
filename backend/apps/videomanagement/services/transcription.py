"""Transcribe source audio into validated, ordered caption words."""
import math
import re
import subprocess
from pathlib import Path

from openai import OpenAI

from apps.apikeysmanagement.models import ApiKeys, Provider
from ..utils.usage import record_usage


def normalize_words(items, duration):
    words, previous_end = [], 0
    for item in items or []:
        start, end = float(item.start), float(item.end)
        if not math.isfinite(start) or not math.isfinite(end):
            continue
        start, end = max(previous_end, 0, start), min(duration, end)
        tokens = re.findall(r"\S{1,40}", item.word.strip())
        if not tokens or end <= start:
            continue
        for index, token in enumerate(tokens):
            token_start = round(start + (end - start) * index / len(tokens), 4)
            token_end = min(duration, round(start + (end - start) * (index + 1) / len(tokens), 4))
            if token_end > token_start and token_end <= duration:
                words.append({"text": token, "start": token_start, "end": token_end})
        previous_end = end
    return words


def transcribe_audio(source, user, duration, directory, *, api_key=None):
    audio = Path(directory, "speech.mp3")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(source),
         "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(audio)],
        capture_output=True, check=True, timeout=120,
    )
    client = OpenAI(api_key=api_key or ApiKeys.key_for(user, Provider.OPENAI), timeout=180, max_retries=1)
    with audio.open("rb") as file:
        result = client.audio.transcriptions.create(
            file=file, model="whisper-1", response_format="verbose_json", timestamp_granularities=["word"],
        )
    record_usage(user, "stt", Provider.OPENAI, "whisper-1", seconds=math.ceil(duration))
    return normalize_words(result.words, duration)
