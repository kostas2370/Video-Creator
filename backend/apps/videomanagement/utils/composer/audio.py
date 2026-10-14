"""Compose voice edits on a fixed visual timeline, including adjacent overlaps."""
from moviepy.editor import AudioFileClip, CompositeAudioClip
from ..audio_editing import narration_file, voice_tracks, scene_audio_segments
from .clips import clip_audio
from .timing import align_audio
from .effects import apply_audio_fades


def compose_edited_audio(scenes, scene_tracks):
    segments = scene_audio_segments(scenes)
    plan = voice_tracks(segments)
    by_id = {str(scene.pk): scene for scene in scenes}
    resources, sounds = [], []
    for track in plan:
        reader = AudioFileClip(narration_file(by_id[track["id"]]).path)
        resources.append(reader)
        sound = reader.subclip(track["trim_start"], track["trim_start"] + track["duration"])
        sound = sound.volumex(track["volume"])
        sound = apply_audio_fades(sound, fade_in=track["fade_in"], fade_out=track["fade_out"])
        sounds.append(sound.set_start(track["start"]))
    for segment in segments:
        image = next(iter(segment.content.scene_images.all()), None)
        original = clip_audio(image)
        if original is not None:
            resources.append(original)
            sounds.append(original.set_start(segment.start))
    duration = sum(duration for _, duration in scene_tracks)
    mixed = CompositeAudioClip(sounds).set_duration(duration) if sounds else align_audio(None, duration)
    resources.extend(sounds)
    return mixed.set_fps(44100), resources
