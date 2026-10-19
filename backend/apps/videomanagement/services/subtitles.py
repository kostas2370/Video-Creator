"""Shared phrase cues for burned-in captions and current-edit SRT exports.

Measured speech timestamps are preferred; estimated timing remains a fallback.
"""
import math
import re
import textwrap
from dataclasses import dataclass

from rest_framework.exceptions import ValidationError

from .speech_alignment import caption_words
from .caption_timing import estimated_words
from .caption_styles import caption_style as caption_style, resolve_style, video_caption_style
from ..models import VideoStatus, VideoType
from ..utils.exceptions import VideoEditConflict
from ..utils.timing import file_timing, scene_timing
from ..utils.audio_editing import narration_file, narration_enabled, audio_bounds, caption_offsets, duration_override


@dataclass(frozen=True)
class CaptionCue:
    start: float
    end: float
    text: str
    active_word: int | None = None


def caption_groups(words, preset="TIKTOK"):
    groups, group = [], []
    style = resolve_style(preset)
    limit, characters = style.max_words, style.max_characters
    for word in words:
        if group and (len(group) >= limit or len(" ".join(item["text"] for item in [*group, word])) > characters or word["start"] - group[-1]["end"] > 0.5):
            groups.append(group)
            group = []
        group.append(word)
        if re.search(r"[.!?;…][\"”’')]*$", word["text"]):
            groups.append(group)
            group = []
    if group:
        groups.append(group)
    return groups


def word_cues(words, preset="TIKTOK", *, highlight=False):
    style = resolve_style(preset)
    cues = []
    for group in caption_groups(words, style):
        text = textwrap.fill(" ".join(word["text"] for word in group), width=style.line_width,
                             break_long_words=False, break_on_hyphens=False)
        if style.highlight_words and highlight:
            for index, word in enumerate(group):
                # Highlight advances at measured word boundaries, preserving pauses between phrases.
                end = group[index+1]["start"] if index+1 < len(group) else word["end"]
                cues.append(CaptionCue(word["start"], end, text, index))
        else:
            cues.append(CaptionCue(group[0]["start"], group[-1]["end"], text))
    return cues


def narration_duration(scene):
    return file_timing(narration_file(scene)).get("audio_duration")


def scene_cues(scene, *, offset=0, duration=None, highlight=False):
    manual = getattr(scene.video, "video_type", None) == VideoType.MANUAL
    if not narration_enabled(scene) and not manual:
        return []
    duration = narration_duration(scene) if duration is None else duration
    if duration is None and manual:
        duration = scene_timing(scene, next(iter(scene.scene_images.all()), None))["base_duration"]
    if duration is None or not math.isfinite(duration) or duration <= 0:
        return []
    style = video_caption_style(scene.video)
    words = caption_words(scene)
    if words is None:
        words = estimated_words(scene.text, duration)
    cues = [CaptionCue(cue.start + offset, cue.end + offset, cue.text, cue.active_word)
            for cue in word_cues(words, style, highlight=highlight)]
    choices = getattr(scene, "audio_settings", None) or {}
    trim_start, trim_end = audio_bounds(scene, duration)
    delay = choices.get("delay", 0)
    override = duration_override(scene)
    if override is not None:
        trim_end = min(trim_end, trim_start + max(0, override - delay))
    return [CaptionCue(max(cue.start - offset, trim_start) - trim_start + offset + delay,
                       min(cue.end - offset, trim_end) - trim_start + offset + delay, cue.text, cue.active_word)
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
