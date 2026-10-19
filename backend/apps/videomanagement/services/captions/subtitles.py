"""Shared phrase cues for burned-in captions and current-edit SRT exports.

Measured speech timestamps are preferred; estimated timing remains a fallback.
"""

import math

from rest_framework.exceptions import ValidationError

from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.models import VideoStatus, VideoType
from apps.videomanagement.services.captions.alignment import caption_words
from apps.videomanagement.services.scenes.timeline import caption_offsets
from apps.videomanagement.utils.audio_editing import (
    audio_bounds,
    duration_override,
    narration_enabled,
    narration_file,
)
from apps.videomanagement.utils.captions.cues import CaptionCue, cues_to_srt, word_cues
from apps.videomanagement.utils.captions.styles import caption_style as caption_style
from apps.videomanagement.utils.captions.styles import (
    video_caption_style,
)
from apps.videomanagement.utils.captions.timing import estimated_words
from apps.videomanagement.utils.timing import file_timing, scene_timing


def narration_duration(scene):
    return file_timing(narration_file(scene)).get("audio_duration")


def scene_cues(scene, *, offset=0, duration=None, highlight=False):
    manual = getattr(scene.video, "video_type", None) == VideoType.MANUAL
    if not narration_enabled(scene) and not manual:
        return []
    duration = narration_duration(scene) if duration is None else duration
    if duration is None and manual:
        duration = scene_timing(scene, next(iter(scene.scene_images.all()), None))[
            "base_duration"
        ]
    if duration is None or not math.isfinite(duration) or duration <= 0:
        return []
    style = video_caption_style(scene.video)
    words = caption_words(scene)
    if words is None:
        words = estimated_words(scene.text, duration)
    cues = [
        CaptionCue(cue.start + offset, cue.end + offset, cue.text, cue.active_word)
        for cue in word_cues(words, style, highlight=highlight)
    ]
    choices = getattr(scene, "audio_settings", None) or {}
    trim_start, trim_end = audio_bounds(scene, duration)
    delay = choices.get("delay", 0)
    override = duration_override(scene)
    if override is not None:
        trim_end = min(trim_end, trim_start + max(0, override - delay))
    return [
        CaptionCue(
            max(cue.start - offset, trim_start) - trim_start + offset + delay,
            min(cue.end - offset, trim_end) - trim_start + offset + delay,
            cue.text,
            cue.active_word,
        )
        for cue in cues
        if cue.end - offset > trim_start and cue.start - offset < trim_end
    ]


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
    cues = []
    scenes = list(video.scenes.with_media())
    intro_offset = offset
    voice_offsets = (
        caption_offsets(scenes)
        if any(scene.audio_settings.get("crossfade") for scene in scenes)
        else {}
    )
    for scene in scenes:
        cues.extend(
            scene_cues(
                scene,
                offset=voice_offsets[str(scene.pk)] + intro_offset
                if str(scene.pk) in voice_offsets
                else offset,
            )
        )
        image = next(iter(scene.scene_images.all()), None)
        offset += scene_timing(scene, image)["duration"]
    if not cues:
        raise ValidationError(
            {
                "detail": "Add caption text or recorded narration before exporting subtitles."
            }
        )
    return cues_to_srt(cues)
