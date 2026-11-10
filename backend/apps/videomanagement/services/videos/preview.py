"""Preview timing calculations; serializers read response fields from the referenced models."""

from dataclasses import dataclass

from rest_framework.exceptions import ValidationError

from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.models import (
    TransitionStyle,
    VideoStatus,
)
from apps.videomanagement.services.captions.subtitles import timeline_caption_words, timeline_cues
from apps.videomanagement.services.scenes.timeline import (
    SegmentTiming,
    scene_segment,
)
from apps.videomanagement.utils.captions.cues import CaptionCue
from apps.videomanagement.utils.cuts import video_sections
from apps.videomanagement.utils.timing import file_timing
from apps.videomanagement.utils.transitions import default_transition, intro_transition


@dataclass
class PreviewTimeline:
    duration: float
    segments: list[SegmentTiming]
    captions: list[CaptionCue]
    caption_words: list | None = None


def asset_segment(asset, kind, start):
    """Opening and closing clips use their own media duration and soundtrack."""
    timing = file_timing(asset.file)
    duration = timing.get("duration")
    if duration is None:
        raise ValidationError(
            {
                "detail": f"The {kind} timing is unavailable. Check its file before previewing."
            }
        )
    return SegmentTiming(
        content=asset,
        kind=kind,
        start=start,
        duration=duration,
        base_duration=duration,
        visual_type="video",
        visual_duration=duration,
        clip_audio=bool(timing.get("audio_duration")),
    )


def intro_segment(video):
    opening = asset_segment(video.intro, "intro", 0)
    opening.transition, opening.transition_duration = intro_transition(
        video.settings or {}
    )
    return opening


def fade_duration(segment, requested):
    return (
        min(requested, segment.duration / 2)
        if requested is not None
        else segment.duration * 0.2
    )


def apply_transitions(segments, choices, opening=None):
    """Apply scene-boundary effects using the renderer's fade and dissolve limits."""
    if opening and opening.transition == TransitionStyle.FADE:
        opening.fade_out = fade_duration(opening, opening.transition_duration)
    for index, segment in enumerate(segments):
        previous = segments[index - 1] if index else opening
        incoming_style = (
            previous.transition
            if previous
            else default_transition(choices)
        )
        if incoming_style == TransitionStyle.FADE:
            requested = (
                previous.transition_duration
                if previous
                else choices.get("transition_duration")
            )
            segment.fade_in = fade_duration(segment, requested)
        if segment.transition == TransitionStyle.FADE:
            segment.fade_out = fade_duration(segment, segment.transition_duration)
        if previous and previous.transition == TransitionStyle.DISSOLVE:
            requested = previous.transition_duration
            segment.dissolve_in = min(
                requested if requested is not None else 0.5,
                previous.duration / 2,
                segment.duration / 2,
            )


def preview_timeline(video):
    """Build ordered timing data from prefetched models; serializers own the response fields."""
    if video.status not in (
        VideoStatus.READY,
        VideoStatus.COMPLETED,
        VideoStatus.FAILED,
    ):
        raise VideoEditConflict(
            "Wait for processing to finish before previewing your edit."
        )
    choices = video.settings or {}
    segments, captions, offset = [], [], 0
    opening = intro_segment(video) if video.intro else None
    if opening:
        segments.append(opening)
        offset += opening.duration

    scenes = list(video.scenes.all())
    if not scenes:
        raise ValidationError({"detail": "Add a scene before previewing your edit."})
    scene_segments = []
    for index, scene in enumerate(scenes, start=1):
        segment = scene_segment(scene, index, offset, choices)
        scene_segments.append(segment)
        offset += segment.duration
    apply_transitions(scene_segments, choices, opening)
    segments.extend(scene_segments)

    if video.outro:
        closing = asset_segment(video.outro, "outro", offset)
        segments.append(closing)
        offset += closing.duration
    words = timeline_caption_words(segments) if choices.get("subtitles", False) else []
    if words:
        captions = timeline_cues(segments, sections=video_sections(video, segments), words=words, highlight=True)
    return PreviewTimeline(duration=offset, segments=segments, captions=captions, caption_words=words)
