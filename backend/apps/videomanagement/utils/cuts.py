"""Non-destructive cuts on the composed source timeline, shared by all outputs."""

import math


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


def cut_cues(cues, sections):
    from .captions.cues import CaptionCue

    result, offset = [], 0
    for section in sections:
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
