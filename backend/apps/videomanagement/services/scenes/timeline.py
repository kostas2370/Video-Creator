"""Scene playback timing shared by preview, audio planning and caption exports."""

from dataclasses import dataclass

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
    return SegmentTiming(
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
