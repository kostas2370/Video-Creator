import json
from pathlib import Path
from types import SimpleNamespace
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

from apps.videomanagement.utils.captions.timing import normalize_words


class TranscriptionError(ValueError):
    pass


def transcribe_local(audio, duration):
    request = Request(
        settings.LOCAL_WHISPER_URL.rstrip("/") + "/transcribe",
        data=Path(audio).read_bytes(),
        headers={"Content-Type": "application/octet-stream"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.LOCAL_WHISPER_TIMEOUT) as response:
            data = json.load(response)
        if not isinstance(data, dict) or not isinstance(data.get("words"), list):
            raise ValueError("Invalid local transcript")
        items = [SimpleNamespace(**word) for word in data["words"]]
        return normalize_words(items, duration)
    except (URLError, OSError, ValueError, TypeError, AttributeError) as exc:
        raise TranscriptionError(
            "Local Whisper could not transcribe this audio. Check that the whisper "
            "Docker service is running and its model has downloaded, then retry. "
            "Saved transcription chunks will be reused."
        ) from exc
