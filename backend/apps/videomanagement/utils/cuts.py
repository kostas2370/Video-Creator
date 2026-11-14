"""Non-destructive cuts on the composed source timeline, shared by all outputs."""

import hashlib
import json
import math

from .captions.cues import CaptionCue


def scene_sections(scene, duration):
    cuts = getattr(scene, "cuts", None) or {}
    # Source duration edits invalidate the old cut coordinates.
    if cuts and math.isclose(cuts.get("source_duration", -1), duration, abs_tol=0.001):
        return cuts["sections"]
    return [{"start": 0, "end": duration}]


def timeline_sections(segments):
    result = []
    for segment in segments:
        sections = (
            scene_sections(segment.content, segment.duration)
            if segment.kind == "scene"
            else [{"start": 0, "end": segment.duration}]
        )
        for section in sections:
            result.append(
                {
                    "start": segment.start + section["start"],
                    "end": segment.start + section["end"],
                }
            )
    return result


def joined_duration(sections):
    return sum(s["end"] - s["start"] for s in sections)


def continuous_sections(sections):
    """A split without removed footage must not split a caption phrase."""
    result = []
    for section in sections:
        if result and abs(result[-1]["end"] - section["start"]) < 1e-9:
            result[-1]["end"] = section["end"]
        else:
            result.append(dict(section))
    return result


def cut_cues(cues, sections):
    result, offset = [], 0
    for section in continuous_sections(sections):
        for cue in cues:
            start, end = max(cue.start, section["start"]), min(cue.end, section["end"])
            if end > start:
                result.append(
                    CaptionCue(
                        offset + start - section["start"],
                        offset + end - section["start"],
                        cue.text,
                        cue.active_word,
                    )
                )
        offset += section["end"] - section["start"]
    return result


def map_sections(source, sections):
    """Map cuts on a joined edit back to the original composed timeline."""
    result = []
    offset = 0
    for part in source:
        length = part["end"] - part["start"]
        for section in sections:
            start = max(offset, section["start"])
            end = min(offset + length, section["end"])
            if end > start:
                result.append({
                    "start": part["start"] + start - offset,
                    "end": part["start"] + end - offset,
                })
        offset += length
    return result


def video_cut_source(segments):
    sections = timeline_sections(segments)
    identity = [
        [s.kind, str(s.content.pk), round(float(s.start), 6), round(float(s.duration), 6),
         getattr(s.content, "cuts", {}) if s.kind == "scene" else {}]
        for s in segments
    ]
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return {"duration": joined_duration(sections), "key": key, "sections": sections}


def video_sections(video, segments):
    source = video_cut_source(segments)
    cuts = video.cuts or {}
    if (cuts.get("source_key") == source["key"]
            and math.isclose(cuts.get("source_duration", -1), source["duration"], abs_tol=0.001)):
        return map_sections(source["sections"], cuts["sections"])
    return source["sections"]
