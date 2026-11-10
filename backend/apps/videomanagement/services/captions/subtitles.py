"""Shared phrase cues for burned-in captions and current-edit SRT exports.

Measured speech timestamps are preferred; estimated timing remains a fallback.
"""

import math

from rest_framework.exceptions import ValidationError

from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.models import VideoStatus, VideoType
from apps.videomanagement.services.captions.alignment import caption_words
from apps.videomanagement.services.scenes.timeline import SegmentTiming, scene_segment
from apps.videomanagement.utils.cuts import continuous_sections, cut_cues, joined_duration, video_sections
from apps.videomanagement.utils.audio_editing import (
    audio_bounds,
    duration_override,
    narration_enabled,
    narration_file,
    voice_tracks,
)
from apps.videomanagement.utils.captions.cues import cues_to_srt, word_cues
from apps.videomanagement.utils.captions.styles import caption_style as caption_style
from apps.videomanagement.utils.captions.styles import (
    video_caption_style,
)
from apps.videomanagement.utils.captions.timing import estimated_words
from apps.videomanagement.utils.timing import file_timing, scene_timing


def narration_duration(scene):
    return file_timing(narration_file(scene)).get("audio_duration")


def scene_caption_words(scene, *, offset=0, duration=None):
    """Resolve words onto scene playback time before grouping them into phrases."""
    manual = getattr(scene.video, "video_type", None) == VideoType.MANUAL
    if not narration_enabled(scene) and not manual:
        return []
    duration = narration_duration(scene) if duration is None else duration
    if duration is None and manual:
        duration = scene_timing(scene, next(iter(scene.scene_images.all()), None))["base_duration"]
    if duration is None or not math.isfinite(duration) or duration <= 0:
        return []
    words = caption_words(scene)
    choices = getattr(scene, "audio_settings", None) or {}
    trim_start, trim_end = audio_bounds(scene, duration)
    delay = choices.get("delay", 0)
    override = duration_override(scene)
    if override is not None:
        trim_end = min(trim_end, trim_start + max(0, override - delay))
    if words is None:
        # Manual captions are authored text; fit estimates to their visible duration.
        if manual:
            words = [{**word, "start": word["start"] + trim_start, "end": word["end"] + trim_start}
                     for word in estimated_words(scene.text, max(0, trim_end - trim_start))]
        else:
            words = estimated_words(scene.text, duration)
    return [
        {"start": max(word["start"], trim_start) - trim_start + offset + delay,
         "end": min(word["end"], trim_end) - trim_start + offset + delay,
         "text": word["text"]}
        for word in words if word["end"] > trim_start and word["start"] < trim_end
    ]


def scene_cues(scene, *, offset=0, duration=None, highlight=False):
    return word_cues(
        scene_caption_words(scene, offset=offset, duration=duration),
        video_caption_style(scene.video), highlight=highlight,
    )


def timeline_caption_words(segments):
    scenes = [segment for segment in segments if getattr(segment, "kind", "scene") == "scene"]
    tracks = (
        {track["id"]: track for track in voice_tracks(scenes)}
        if any(segment.content.audio_settings.get("crossfade") for segment in scenes)
        else {}
    )
    words = []
    for segment in scenes:
        scene = segment.content
        track = tracks.get(str(scene.pk))
        offset = track["start"] - scene.audio_settings.get("delay", 0) if track else segment.start
        words.extend({**word, "scene_id": str(scene.pk)} for word in scene_caption_words(scene, offset=offset, duration=segment.narration_duration))
    return words


def timeline_cues(segments, *, sections=None, highlight=False, words=None):
    """Group each scene's retained words, keeping source times until final joining."""
    scenes = [segment for segment in segments if getattr(segment, "kind", "scene") == "scene"]
    if not scenes:
        return []
    if words is None:
        words = timeline_caption_words(scenes)
    style = video_caption_style(scenes[0].content.video)
    if sections is None:
        sections = [{"start": 0, "end": float("inf")}]
    by_scene = {}
    for word in words:
        by_scene.setdefault(word["scene_id"], []).append(word)
    cues = []
    for section in continuous_sections(sections):
        for scene_words in by_scene.values():
            kept = [
                {**word, "start": max(word["start"], section["start"]), "end": min(word["end"], section["end"])}
                for word in scene_words if word["end"] > section["start"] + 1e-9 and word["start"] < section["end"] - 1e-9
            ]
            cues.extend(word_cues(kept, style, highlight=highlight))
    return sorted(cues, key=lambda cue: cue.start)


def export_subtitles(video):
    if video.status not in (
        VideoStatus.READY,
        VideoStatus.COMPLETED,
        VideoStatus.FAILED,
    ):
        raise VideoEditConflict(
            "Wait for processing to finish before downloading subtitles."
        )
    if (
        video.video_type != VideoType.MANUAL
        and not (video.settings or {}).get("narration", True)
        and not video.scenes.exclude(voiceover="").exists()
    ):
        raise ValidationError({"detail": "Subtitles need recorded narration."})
    offset = 0
    if video.intro:
        offset = file_timing(video.intro.file).get("duration")
        if offset is None:
            raise ValidationError(
                {
                    "detail": "The intro timing is unavailable. Check the intro file before exporting."
                }
            )
    scenes = list(video.scenes.with_media())
    intro_offset = offset
    raw_segments, start = [], intro_offset
    for index, scene in enumerate(scenes, 1):
        segment = scene_segment(scene, index, start, video.settings or {})
        raw_segments.append(segment)
        start += segment.duration
    if intro_offset:
        raw_segments.insert(0, SegmentTiming(
            content=video.intro, kind="intro", start=0, duration=intro_offset,
            base_duration=intro_offset, visual_type="video",
        ))
    if video.outro and video.cuts:
        closing_duration = file_timing(video.outro.file).get("duration")
        if closing_duration is None:
            raise ValidationError({"detail": "Check the outro file before exporting full-video cuts."})
        raw_segments.append(SegmentTiming(
            content=video.outro, kind="outro", start=start, duration=closing_duration,
            base_duration=closing_duration, visual_type="video",
        ))
        start += closing_duration
    words = timeline_caption_words(raw_segments)
    if not words:
        raise ValidationError({"detail": "Add caption text or recorded narration before exporting subtitles."})
    sections = video_sections(video, raw_segments)
    cues = timeline_cues(raw_segments, sections=sections, words=words)
    if joined_duration(sections) < start - 1e-9:
        cues = cut_cues(cues, sections)
    return cues_to_srt(cues)
