"""Scene playback timing shared by preview, audio planning and caption exports."""

from copy import copy
from dataclasses import dataclass, field

from apps.videomanagement.models import Intro, Outro, Scene, SceneImage, TransitionStyle
from apps.videomanagement.utils.audio_editing import (
    narration_enabled,
    narration_file,
    voice_tracks,
)
from apps.videomanagement.utils.file_utils import check_if_video
from apps.videomanagement.utils.timing import file_timing, scene_timing
from apps.videomanagement.utils.transitions import scene_transition


@dataclass
class SegmentTiming:
    content: Scene | Intro | Outro
    kind: str
    start: float
    duration: float
    base_duration: float
    visual_type: str
    image: SceneImage | None = None
    index: int = 0
    visual_duration: float | None = None
    loop_visual: bool = False
    clip_audio: bool = False
    narration_duration: float | None = None
    transition: str = TransitionStyle.CUT
    transition_duration: float | None = None
    shots: list = field(default_factory=list)
    trim_start: float = 0
    fade_in: float = 0
    fade_out: float = 0
    dissolve_in: float = 0


def scene_segment(scene, index, start, choices):
    """Resolve the scene's playback duration, media timing and transition override."""
    image = next(iter(scene.scene_images.all()), None)
    timing = scene_timing(scene, image)
    speech = (
        file_timing(narration_file(scene)).get("audio_duration")
        if narration_enabled(scene)
        else None
    )
    is_video = bool(image and image.file and check_if_video(image.file.name))
    visual_timing = file_timing(image.file) if is_video else {}
    style, transition_duration = scene_transition(scene, choices)
    segment = SegmentTiming(
        content=scene,
        image=image,
        kind="scene",
        index=index,
        start=start,
        duration=timing["duration"],
        base_duration=timing["base_duration"],
        visual_type="video" if is_video else "image",
        visual_duration=visual_timing.get("duration"),
        loop_visual=is_video and choices.get("loop_visual", False),
        clip_audio=bool(
            is_video and image.with_audio and visual_timing.get("audio_duration")
        ),
        narration_duration=speech,
        transition=style,
        transition_duration=transition_duration,
    )

    images = list(scene.scene_images.all())
    if len(images) > 1 or (
        image and (image.trim_start or image.motion_style or image.motion_intensity)
    ):
        total = sum(row.timing_weight for row in images)
        offset = 0
        for index, row in enumerate(images):
            duration = segment.base_duration * row.timing_weight / total
            shot = copy(segment)
            shot.content = copy(scene)
            shot.content.motion_style = row.motion_style or scene.motion_style
            shot.content.motion_intensity = (
                row.motion_intensity or scene.motion_intensity
            )
            shot.shots = []
            shot.image = row
            shot.start = offset
            shot.base_duration = duration
            shot.duration = duration + (
                scene.pause_after if index == len(images) - 1 else 0
            )
            shot.trim_start = row.trim_start
            is_clip = bool(row.file and check_if_video(row.file.name))
            metadata = file_timing(row.file) if is_clip else {}
            shot.visual_type = "video" if is_clip else "image"
            shot.visual_duration = (
                max(0, metadata.get("duration", 0) - row.trim_start)
                if is_clip
                else None
            )
            shot.loop_visual = is_clip and choices.get("loop_visual", False)
            shot.clip_audio = bool(
                is_clip and row.with_audio and metadata.get("audio_duration")
            )
            segment.shots.append(shot)
            offset += duration
    return segment


def scene_audio_segments(scenes):
    segments, offset = [], 0
    for index, scene in enumerate(scenes, 1):
        segment = scene_segment(scene, index, offset, scene.video.settings or {})
        segments.append(segment)
        offset += segment.duration
    return segments


def caption_offsets(scenes):
    by_id = {str(scene.pk): scene for scene in scenes}
    return {
        track["id"]: track["start"]
        - (by_id[track["id"]].audio_settings or {}).get("delay", 0)
        for track in voice_tracks(scene_audio_segments(scenes))
    }
