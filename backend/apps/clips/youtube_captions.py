import logging
import math
from types import SimpleNamespace
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from django.conf import settings
from pytubefix import YouTube

from apps.videomanagement.utils.captions.timing import normalize_words, words_in_range

logger = logging.getLogger(__name__)


def track_language(code):
    return code.removeprefix("a.").split("-")[0]


def source_tracks(video):
    tracks = list(video.captions)
    renderer = video.vid_info.get("captions", {}).get(
        "playerCaptionsTracklistRenderer", {}
    )
    audio_tracks = renderer.get("audioTracks", [])
    language = None
    if audio_tracks:
        audio = audio_tracks[renderer.get("defaultAudioTrackIndex", 0)]
        index = audio.get("defaultCaptionTrackIndex")
        if index is not None:
            original = renderer["captionTracks"][index]
            language = track_language(original["vssId"].strip("."))
    if language is None:
        automatic = {
            track_language(track.code)
            for track in tracks
            if track.code.startswith("a.")
        }
        languages = automatic or {track_language(track.code) for track in tracks}
        if len(languages) != 1:
            return []
        language = languages.pop()
    return sorted(
        (track for track in tracks if track_language(track.code) == language),
        key=lambda track: not track.code.startswith("a."),
    )


def caption_words(data, start, stop, duration):
    items, seen = [], set()
    for event in data.get("events", []):
        segments = [
            segment
            for segment in event.get("segs", [])
            if segment.get("utf8", "").strip()
        ]
        if not segments:
            continue
        base = float(event["tStartMs"]) / 1000
        end = base + float(event["dDurationMs"]) / 1000
        if end <= start or base >= stop:
            continue
        for index, segment in enumerate(segments):
            text = segment["utf8"].strip()
            if len(text.split()) != 1 or (index and "tOffsetMs" not in segment):
                return None
            offset = float(segment.get("tOffsetMs", 0)) / 1000
            begin = base + offset
            if (
                not all(math.isfinite(value) for value in (begin, end, offset))
                or offset < 0
                or end <= begin
            ):
                return None
            key = (round(begin, 4), text)
            if key not in seen:
                items.append(SimpleNamespace(word=text, start=begin, end=end))
                seen.add(key)
    items.sort(key=lambda word: word.start)
    for word, following in zip(items, items[1:]):
        if word.start == following.start:
            return None
        word.end = min(word.end, following.start)
    selected = words_in_range(normalize_words(items, duration), start, stop)
    tolerance = min(30, max(3, (stop - start) * 0.05))
    if (
        not selected
        or selected[0]["start"] > start + tolerance
        or selected[-1]["end"] < stop - tolerance
        or any(
            right["start"] - left["end"] > 60
            for left, right in zip(selected, selected[1:])
        )
    ):
        return None
    return selected


def youtube_transcript(project):
    if not project.youtube_url or not settings.YOUTUBE_CAPTIONS_ENABLED:
        return None
    try:
        tracks = source_tracks(YouTube(project.youtube_url))
    except Exception:
        logger.info("YouTube captions unavailable; using audio transcription")
        return None
    for track in tracks:
        try:
            url = urlsplit(track.url)
            query = dict(parse_qsl(url.query))
            query["fmt"] = "json3"
            response = requests.get(
                urlunsplit(url._replace(query=urlencode(query))), timeout=(5, 20)
            )
            response.raise_for_status()
            words = caption_words(
                response.json(),
                project.range_start,
                project.range_stop,
                project.duration,
            )
            if words:
                kind = "automatic" if track.code.startswith("a.") else "uploaded"
                return words, f"YouTube captions ({track_language(track.code)}, {kind})"
        except (
            requests.RequestException,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
        ):
            logger.info(
                "YouTube caption track unavailable or unsuitable; trying another track"
            )
    return None
