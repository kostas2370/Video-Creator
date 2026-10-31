from pathlib import Path
from types import SimpleNamespace

import requests
from django.conf import settings

from apps.videomanagement.utils.captions.timing import normalize_words


class TranscriptionError(ValueError):
    pass


def transcribe_local(audio, duration):
    try:
        with Path(audio).open("rb") as file:
            response = requests.post(
                settings.LOCAL_WHISPER_URL.rstrip("/") + "/transcribe",
                data=file,
                headers={"Content-Type": "application/octet-stream"},
                timeout=(5, settings.LOCAL_WHISPER_TIMEOUT),
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("words"), list):
            raise ValueError("Invalid local transcript")
        items = [SimpleNamespace(**word) for word in data["words"]]
        return normalize_words(items, duration)
    except (
        requests.RequestException,
        OSError,
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:
        raise TranscriptionError(
            "Local Whisper could not transcribe this audio. Check that the whisper "
            "Docker service is running and its model has downloaded, then retry. "
            "Saved transcription chunks will be reused."
        ) from exc
