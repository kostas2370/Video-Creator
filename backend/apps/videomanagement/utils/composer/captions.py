"""Translate resolved caption styles and timed cues into an ASS document."""

import re

from apps.videomanagement.services.captions.subtitles import scene_cues
from apps.videomanagement.utils.captions.styles import (
    resolve_style,
    video_caption_style,
)

from ..audio_editing import voice_tracks
from .ass import (
    ass_color,
    ass_event,
    document_header,
    escape_ass_text,
    write_document,
)


def caption_style_fields(style, size):
    layout = style.layout(size)
    values = {
        "Fontname": style.font,
        "Fontsize": layout["font_size"],
        "PrimaryColour": ass_color(style.color),
        "SecondaryColour": ass_color(style.highlight_color),
        "OutlineColour": ass_color(style.outline_color),
        "Bold": -1 if style.bold else 0,
        "Outline": layout["outline"],
        "Shadow": layout["shadow"],
        "Alignment": layout["alignment"],
        "MarginL": layout["margin_left"],
        "MarginR": layout["margin_right"],
        "MarginV": layout["margin_vertical"],
    }
    return values


def ass_header(style, size):
    return document_header(size, [caption_style_fields(style, size)])


def caption_ass_text(cue, *, style):
    """Escape user text before inserting controlled word-color tags."""
    text = escape_ass_text(cue.text)
    if style.uppercase:
        text = text.upper()
    if style.highlight_words:
        word_index = -1

        def color_word(match):
            nonlocal word_index
            word_index += 1
            if word_index != cue.active_word:
                return match.group()
            return (
                "{\\1c"
                + ass_color(style.highlight_color)
                + "}"
                + match.group()
                + "{\\1c"
                + ass_color(style.color)
                + "}"
            )

        text = re.sub(r"\S+", color_word, text)
    return text.replace("\n", "\\N")


def write_captions(path, segments, size):
    style = (
        video_caption_style(segments[0].content.video)
        if segments
        else resolve_style("CLASSIC")
    )
    tracks = (
        {track["id"]: track for track in voice_tracks(segments)}
        if any(segment.content.audio_settings.get("crossfade") for segment in segments)
        else {}
    )
    cues = []
    for segment in segments:
        scene = segment.content
        track = tracks.get(str(scene.pk))
        offset = (
            track["start"] - scene.audio_settings.get("delay", 0)
            if track
            else segment.start
        )
        cues.extend(
            scene_cues(
                scene,
                offset=offset,
                duration=segment.narration_duration,
                highlight=True,
            )
        )
    write_ass(path, cues, size, style)


def write_ass(path, cues, size, style):
    lines = []
    for cue in cues:
        text = caption_ass_text(cue, style=style)
        scale = style.text_scale(cue.text, size)
        if scale < 1:
            percent = round(scale * 100, 3)
            text = "{\\fscx" + str(percent) + "\\fscy" + str(percent) + "}" + text
        lines.append(ass_event(cue.start, cue.end, text))
    write_document(path, size, [caption_style_fields(style, size)], lines)
