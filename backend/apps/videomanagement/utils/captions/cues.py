import re
import textwrap
from dataclasses import dataclass

from .styles import resolve_style


@dataclass(frozen=True)
class CaptionCue:
    start: float
    end: float
    text: str
    active_word: int | None = None


def caption_groups(words, preset="TIKTOK"):
    groups, group = [], []
    style = resolve_style(preset)
    limit, characters = style.max_words, style.max_characters
    for word in words:
        if group and (
            len(group) >= limit
            or len(" ".join(item["text"] for item in [*group, word])) > characters
            or word["start"] - group[-1]["end"] > 0.5
        ):
            groups.append(group)
            group = []
        group.append(word)
        if re.search(r"[.!?;…][\"”’')]*$", word["text"]):
            groups.append(group)
            group = []
    if group:
        groups.append(group)
    return groups


def word_cues(words, preset="TIKTOK", *, highlight=False):
    style = resolve_style(preset)
    cues = []
    for group in caption_groups(words, style):
        text = textwrap.fill(
            " ".join(word["text"] for word in group),
            width=style.line_width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        if style.highlight_words and highlight:
            for index, word in enumerate(group):
                # Highlight advances at measured word boundaries, preserving pauses between phrases.
                end = (
                    group[index + 1]["start"] if index + 1 < len(group) else word["end"]
                )
                cues.append(CaptionCue(word["start"], end, text, index))
        else:
            cues.append(CaptionCue(group[0]["start"], group[-1]["end"], text))
    return cues


def srt_timestamp(seconds):
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def cues_to_srt(cues):
    return "\n\n".join(
        f"{number}\n{srt_timestamp(cue.start)} --> {srt_timestamp(cue.end)}\n{cue.text}"
        for number, cue in enumerate(cues, 1)
    ) + ("\n" if cues else "")
