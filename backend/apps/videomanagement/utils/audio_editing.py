"""Audio timing and envelopes shared by editor manifests and rendering."""
import hashlib
import os
import subprocess

import numpy as np
from django.core.cache import cache


def narration_file(scene):
    return getattr(scene, "voiceover", None) or scene.file


def narration_enabled(scene):
    return bool(getattr(scene, "voiceover", None)) or (scene.video.settings or {}).get("narration", True)


def audio_bounds(scene, duration):
    choices = getattr(scene, "audio_settings", None) or {}
    start = min(choices.get("trim_start", 0), duration)
    end = min(choices.get("trim_end") or duration, duration)
    return start, max(start, end)


def edited_duration(scene, duration):
    if duration is None:
        return None
    start, end = audio_bounds(scene, duration)
    return end - start + (getattr(scene, "audio_settings", None) or {}).get("delay", 0)


def waveform(path):
    """Bounded mono analysis; cache against file identity, including replacements."""
    stat = os.stat(path)
    key = "audio-waveform:v1:" + hashlib.sha256(f"{path}:{stat.st_size}:{stat.st_mtime_ns}".encode()).hexdigest()
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-t", "900", "-vn",
                             "-ac", "1", "-ar", "8000", "-f", "f32le", "pipe:1"],
                            capture_output=True, timeout=30, check=True)
    samples = np.frombuffer(result.stdout, dtype="<f4")
    if not len(samples):
        raise ValueError("No audio samples found.")
    peaks = [round(float(np.max(np.abs(chunk))), 4) for chunk in np.array_split(samples, min(600, len(samples)))]
    intervals = []
    # RMS above -40 dB marks activity; short silent gaps belong to the same phrase.
    for index in range(0, len(samples), 800):
        chunk = samples[index:index + 800]
        if float(np.sqrt(np.mean(chunk ** 2))) < 0.01:
            continue
        start, end = index / 8000, min((index + 800) / 8000, len(samples) / 8000)
        if intervals and start - intervals[-1][1] < 0.25:
            intervals[-1][1] = end
        else:
            intervals.append([start, end])
    value = {"duration": len(samples) / 8000, "peaks": peaks, "speech": intervals}
    cache.set(key, value, 3600)
    return value


def voice_tracks(segments):
    tracks = []
    previous = None
    for segment in segments:
        scene = segment.content
        duration = segment.narration_duration
        if segment.kind != "scene" or not duration:
            previous = None
            continue
        choices = getattr(scene, "audio_settings", None) or {}
        trim_start, trim_end = audio_bounds(scene, duration)
        length = trim_end - trim_start
        if length <= 0:
            continue
        start = segment.start + choices.get("delay", 0)
        fade_in = min(choices.get("fade_in", 0), length / 2)
        overlap = 0
        # Crossfade only adjacent voice clips that reach the scene boundary.
        if previous and abs(previous["start"] + previous["duration"] - start) < 0.02:
            overlap = min(previous.pop("crossfade"), previous["duration"] / 2, length / 2)
            previous["fade_out"] = max(previous["fade_out"], overlap)
            start -= overlap
            fade_in = max(fade_in, overlap)
        track = {"id": str(scene.pk), "source": narration_file(scene).url, "start": start,
                 "duration": length, "trim_start": trim_start, "fade_in": fade_in,
                 "fade_out": min(choices.get("fade_out", 0), length / 2),
                 "volume": choices.get("volume", 1), "crossfade": choices.get("crossfade", 0)}
        try:
            activity = waveform(narration_file(scene).path)["speech"]
        except (OSError, ValueError, subprocess.SubprocessError):
            activity = [[trim_start, trim_end]]
        track["speech"] = [[start + max(a, trim_start) - trim_start, start + min(b, trim_end) - trim_start]
                           for a, b in activity if b > trim_start and a < trim_end and track["volume"] > 0]
        tracks.append(track)
        previous = track
    for track in tracks:
        track.pop("crossfade", None)
    return tracks


def scene_audio_segments(scenes):
    # Local import avoids a timing/preview import cycle.
    from ..services.preview import scene_segment
    segments, offset = [], 0
    for index, scene in enumerate(scenes, 1):
        segment = scene_segment(scene, index, offset, scene.video.settings or {})
        segments.append(segment)
        offset += segment.duration
    return segments


def caption_offsets(scenes):
    by_id = {str(scene.pk): scene for scene in scenes}
    return {track["id"]: track["start"] - (by_id[track["id"]].audio_settings or {}).get("delay", 0)
            for track in voice_tracks(scene_audio_segments(scenes))}


def music_gain(t, duration, choices, speech):
    times = np.asarray(t)
    fade_in = min(choices.get("music_fade_in", min(4, duration * 0.1)), duration / 2)
    fade_out = min(choices.get("music_fade_out", min(4, duration * 0.1)), duration / 2)
    gain = np.ones_like(times, dtype=float)
    if fade_in:
        gain *= np.clip(times / fade_in, 0, 1)
    if fade_out:
        gain *= np.clip((duration - times) / fade_out, 0, 1)
    if choices.get("music_ducking", False):
        activity = np.zeros_like(times, dtype=float)
        attack = choices.get("duck_attack", 0.2)
        release = choices.get("duck_release", 0.8)
        for start, end in speech:
            envelope = np.minimum(np.clip((times - start + attack) / attack, 0, 1),
                                  np.clip((end + release - times) / release, 0, 1))
            activity = np.maximum(activity, envelope)
        gain *= 1 - activity * (1 - choices.get("duck_level", 0.25))
    return gain * choices.get("music_volume", 0.07)
