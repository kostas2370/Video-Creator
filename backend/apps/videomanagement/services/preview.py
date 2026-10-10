"""Read-only browser preview of the current edit, using the render's timing rules."""
from dataclasses import dataclass

from rest_framework.exceptions import ValidationError

from ..models import VideoStatus
from ..utils.exceptions import VideoEditConflict
from ..utils.file_utils import check_if_image, check_if_video, stored_file_exists
from ..utils.timing import file_timing, scene_timing
from ..utils.transitions import scene_transition
from ..video_formats import output_size
from .subtitles import CaptionCue, scene_cues


@dataclass
class PreviewSegment:
    id: str
    kind: str
    label: str
    start: float
    duration: float
    base_duration: float
    visual: str | None
    visual_type: str
    text: str | None = None
    pause: float = 0
    visual_duration: float | None = None
    clip_audio: bool = False
    narration: str | None = None
    narration_duration: float | None = None
    transition: str = "CUT"
    transition_duration: float | None = None
    fade_in: float = 0
    fade_out: float = 0
    dissolve_in: float = 0


@dataclass
class PreviewTimeline:
    duration: float
    size: tuple[int, int]
    segments: list[PreviewSegment]
    captions: list[CaptionCue]
    render_only: list[str]


def media_url(field):
    return field.url if stored_file_exists(field) else None


def preview_manifest(video):
    if video.status not in (VideoStatus.READY, VideoStatus.COMPLETED, VideoStatus.FAILED):
        raise VideoEditConflict("Wait for processing to finish before previewing your edit.")
    choices = video.settings or {}
    segments, captions, offset = [], [], 0

    def asset_segment(asset, kind):
        nonlocal offset
        if not asset:
            return
        timing = file_timing(asset.file)
        duration = timing.get("duration")
        if duration is None:
            raise ValidationError({"detail": f"The {kind} timing is unavailable. Check its file before previewing."})
        segments.append(PreviewSegment(
            id=f"{kind}-{asset.pk}", kind=kind, label=kind.title(), start=offset,
            duration=duration, base_duration=duration, visual=media_url(asset.file),
            visual_type="video", visual_duration=duration,
            clip_audio=bool(timing.get("audio_duration")),
        ))
        offset += duration

    asset_segment(video.intro, "intro")
    scene_segments = []
    scenes = list(video.scenes.select_related("video").prefetch_related("scene_images"))
    if not scenes:
        raise ValidationError({"detail": "Add a scene before previewing your edit."})
    for index, scene in enumerate(scenes):
        image = next(iter(scene.scene_images.all()), None)
        timing = scene_timing(scene, image)
        speech = file_timing(scene.file).get("audio_duration") if choices.get("narration", True) else None
        visual = media_url(image.file) if image else None
        is_video = bool(image and image.file and check_if_video(image.file.name))
        if image and image.file and not is_video and not check_if_image(image.file.name):
            visual = None
        visual_timing = file_timing(image.file) if is_video else {}
        style, duration = scene_transition(scene, choices)
        segment = PreviewSegment(
            id=str(scene.pk), kind="scene", label=f"Scene {index + 1}", text=scene.text,
            start=offset, duration=timing["duration"], base_duration=timing["base_duration"],
            pause=scene.pause_after, visual=visual, visual_type="video" if is_video else "image",
            visual_duration=visual_timing.get("duration"),
            clip_audio=bool(is_video and image.with_audio and visual_timing.get("audio_duration")),
            narration=media_url(scene.file) if speech else None, narration_duration=speech,
            transition=style, transition_duration=duration,
        )
        scene_segments.append(segment)
        if choices.get("subtitles", False):
            captions.extend(scene_cues(scene, offset=offset, duration=speech))
        offset += timing["duration"]

    def fade_duration(segment, requested):
        return min(requested, segment.duration / 2) if requested is not None else segment.duration * 0.2

    for index, segment in enumerate(scene_segments):
        previous = scene_segments[index - 1] if index else None
        if previous is None or previous.transition == "FADE":
            requested = previous.transition_duration if previous else choices.get("transition_duration")
            segment.fade_in = fade_duration(segment, requested)
        if segment.transition == "FADE":
            segment.fade_out = fade_duration(segment, segment.transition_duration)
        if previous and previous.transition == "DISSOLVE":
            requested = previous.transition_duration
            segment.dissolve_in = min(
                requested if requested is not None else 0.5,
                previous.duration / 2, segment.duration / 2,
            )
    segments.extend(scene_segments)
    asset_segment(video.outro, "outro")
    return PreviewTimeline(
        duration=offset, size=output_size(choices.get("video_format")),
        segments=segments, captions=captions,
        render_only=[name for name, enabled in (("avatar animation", video.avatar_id),
                     ("background music", video.music_id), ("background effects", video.background_id)) if enabled],
    )
