"""Preview timing calculations; serializers read response fields from the referenced models."""
from dataclasses import dataclass

from rest_framework.exceptions import ValidationError

from ..models import Intro, Outro, Scene, SceneImage, VideoStatus
from ..utils.exceptions import VideoEditConflict
from ..utils.file_utils import check_if_video
from ..utils.timing import file_timing, scene_timing
from ..utils.transitions import scene_transition
from .subtitles import CaptionCue, scene_cues


@dataclass
class PreviewSegmentTiming:
    source: Scene | Intro | Outro
    kind: str
    start: float
    duration: float
    base_duration: float
    visual_type: str
    image: SceneImage | None = None
    index: int = 0
    visual_duration: float | None = None
    clip_audio: bool = False
    narration_duration: float | None = None
    transition: str = "CUT"
    transition_duration: float | None = None
    fade_in: float = 0
    fade_out: float = 0
    dissolve_in: float = 0


@dataclass
class PreviewTimeline:
    duration: float
    segments: list[PreviewSegmentTiming]
    captions: list[CaptionCue]


def preview_timeline(video):
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
        segments.append(PreviewSegmentTiming(
            source=asset, kind=kind, start=offset,
            duration=duration, base_duration=duration,
            visual_type="video", visual_duration=duration,
            clip_audio=bool(timing.get("audio_duration")),
        ))
        offset += duration

    asset_segment(video.intro, "intro")
    scene_segments = []
    scenes = list(video.scenes.all())
    if not scenes:
        raise ValidationError({"detail": "Add a scene before previewing your edit."})
    for index, scene in enumerate(scenes):
        image = next(iter(scene.scene_images.all()), None)
        timing = scene_timing(scene, image)
        speech = file_timing(scene.file).get("audio_duration") if choices.get("narration", True) else None
        is_video = bool(image and image.file and check_if_video(image.file.name))
        visual_timing = file_timing(image.file) if is_video else {}
        style, duration = scene_transition(scene, choices)
        segment = PreviewSegmentTiming(
            source=scene, image=image, kind="scene", index=index + 1,
            start=offset, duration=timing["duration"], base_duration=timing["base_duration"],
            visual_type="video" if is_video else "image",
            visual_duration=visual_timing.get("duration"),
            clip_audio=bool(is_video and image.with_audio and visual_timing.get("audio_duration")),
            narration_duration=speech,
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
        duration=offset,
        segments=segments, captions=captions,
    )
