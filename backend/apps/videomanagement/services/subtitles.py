"""Shared phrase cues for burned-in captions and current-edit SRT exports.

Phrase timing is estimated from text length and the actual narration duration;
voice providers currently return audio without alignment timestamps.
"""
import math
import re
import textwrap
from dataclasses import dataclass

from rest_framework.exceptions import ValidationError

from ..models import VideoStatus, VideoType
from ..utils.exceptions import VideoEditConflict
from ..utils.timing import file_timing, scene_timing
from ..utils.audio_editing import narration_file, narration_enabled, audio_bounds, caption_offsets, duration_override


@dataclass(frozen=True)
class CaptionCue:
    start: float
    end: float
    text: str


def caption_phrases(text, width=32, max_words=10):
    wrapper = textwrap.TextWrapper(width=width, break_on_hyphens=False)
    words = re.findall(r"\S+", text or "")
    # An unusually long token must still fit inside a two-line caption.
    words = [word[i:i + width * 2] for word in words for i in range(0, len(word), width * 2)]
    phrases, current = [], []
    for word in words:
        candidate = [*current, word]
        if current and (len(candidate) > max_words or len(wrapper.wrap(" ".join(candidate))) > 2):
            phrases.append("\n".join(wrapper.wrap(" ".join(current))))
            current = []
        current.append(word)
        if re.search(r'[.!?;…]["”’\')]*$', word):
            phrases.append("\n".join(wrapper.wrap(" ".join(current))))
            current = []
    if current:
        phrases.append("\n".join(wrapper.wrap(" ".join(current))))
    return phrases


def narration_duration(scene):
    return file_timing(narration_file(scene)).get("audio_duration")


def scene_cues(scene, *, offset=0, duration=None):
    manual = getattr(scene.video, "video_type", None) == VideoType.MANUAL
    if not narration_enabled(scene) and not manual:
        return []
    duration = narration_duration(scene) if duration is None else duration
    if duration is None and manual:
        duration = scene_timing(scene, next(iter(scene.scene_images.all()), None))["base_duration"]
    if duration is None or not math.isfinite(duration) or duration <= 0:
        return []
    phrases = caption_phrases(scene.text)
    weights = [max(1, len(re.sub(r"\s", "", text))) for text in phrases]
    total = sum(weights)
    cues, consumed = [], 0
    for text, weight in zip(phrases, weights):
        start = offset + duration * consumed / total
        consumed += weight
        end = offset + duration * consumed / total
        cues.append(CaptionCue(start, end, text))
    choices = getattr(scene, "audio_settings", None) or {}
    trim_start, trim_end = audio_bounds(scene, duration)
    delay = choices.get("delay", 0)
    override = duration_override(scene)
    if override is not None:
        trim_end = min(trim_end, trim_start + max(0, override - delay))
    return [CaptionCue(max(cue.start - offset, trim_start) - trim_start + offset + delay,
                       min(cue.end - offset, trim_end) - trim_start + offset + delay, cue.text)
            for cue in cues if cue.end - offset > trim_start and cue.start - offset < trim_end]


def srt_timestamp(seconds):
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def cues_to_srt(cues):
    return "\n\n".join(
        f"{number}\n{srt_timestamp(cue.start)} --> {srt_timestamp(cue.end)}\n{cue.text}"
        for number, cue in enumerate(cues, 1)
    ) + ("\n" if cues else "")


def export_subtitles(video):
    if video.status not in (VideoStatus.READY, VideoStatus.COMPLETED, VideoStatus.FAILED):
        raise VideoEditConflict("Wait for processing to finish before downloading subtitles.")
    if video.video_type != VideoType.MANUAL and not (video.settings or {}).get("narration", True) and not video.scenes.exclude(voiceover="").exists():
        raise ValidationError({"detail": "Subtitles need recorded narration."})
    offset = 0
    if video.intro:
        offset = file_timing(video.intro.file).get("duration")
        if offset is None:
            raise ValidationError({"detail": "The intro timing is unavailable. Check the intro file before exporting."})
    cues = []
    scenes = list(video.scenes.with_media())
    intro_offset = offset
    voice_offsets = caption_offsets(scenes) if any(scene.audio_settings.get("crossfade") for scene in scenes) else {}
    for scene in scenes:
        cues.extend(scene_cues(scene, offset=voice_offsets[str(scene.pk)] + intro_offset if str(scene.pk) in voice_offsets else offset))
        image = next(iter(scene.scene_images.all()), None)
        offset += scene_timing(scene, image)["duration"]
    if not cues:
        raise ValidationError({"detail": "Add caption text or recorded narration before exporting subtitles."})
    return cues_to_srt(cues)
