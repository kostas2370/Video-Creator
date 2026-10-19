"""Translate resolved caption styles and timed cues into an ASS document."""
import re
from pathlib import Path

from ...services.caption_styles import resolve_style, video_caption_style
from ...services.subtitles import scene_cues
from ..audio_editing import voice_tracks

ASS_STYLE_FIELDS = (
    "Name", "Fontname", "Fontsize", "PrimaryColour", "SecondaryColour", "OutlineColour",
    "BackColour", "Bold", "Italic", "Underline", "StrikeOut", "ScaleX", "ScaleY",
    "Spacing", "Angle", "BorderStyle", "Outline", "Shadow", "Alignment", "MarginL",
    "MarginR", "MarginV", "Encoding",
)
ASS_EVENT_FIELDS = "Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"


def ass_timestamp(value):
    ticks = max(0, round(value * 100))
    return f"{ticks // 360000}:{ticks // 6000 % 60:02}:{ticks // 100 % 60:02}.{ticks % 100:02}"


def ass_color(color):
    return "&H00" + (color[5:7] + color[3:5] + color[1:3]).upper() + "&"


def ass_header(style, size):
    layout = style.layout(size)
    font = style.font.replace("-", " ").replace(",", " ").replace("\n", " ").replace("\r", " ")
    values = {
        "Name": "Default", "Fontname": font, "Fontsize": layout["font_size"],
        "PrimaryColour": ass_color(style.color), "SecondaryColour": ass_color(style.highlight_color),
        "OutlineColour": ass_color(style.outline_color), "BackColour": "&H80000000",
        "Bold": -1 if style.bold else 0, "Italic": 0, "Underline": 0, "StrikeOut": 0,
        "ScaleX": 100, "ScaleY": 100, "Spacing": 0, "Angle": 0, "BorderStyle": 1,
        "Outline": layout["outline"], "Shadow": layout["shadow"], "Alignment": layout["alignment"],
        "MarginL": layout["margin_left"], "MarginR": layout["margin_right"],
        "MarginV": layout["margin_vertical"], "Encoding": 1,
    }
    return "\n".join([
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {size[0]}", f"PlayResY: {size[1]}",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "[V4+ Styles]",
        "Format: " + ", ".join(ASS_STYLE_FIELDS),
        "Style: " + ",".join(str(values[field]) for field in ASS_STYLE_FIELDS),
        "[Events]", "Format: " + ASS_EVENT_FIELDS, "",
    ])


def caption_ass_text(cue, *, style):
    """Escape user text before inserting controlled word-color tags."""
    text = cue.text.replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\r", "")
    if style.uppercase:
        text = text.upper()
    if style.highlight_words:
        word_index = -1

        def color_word(match):
            nonlocal word_index
            word_index += 1
            if word_index != cue.active_word:
                return match.group()
            return "{\\1c" + ass_color(style.highlight_color) + "}" + match.group() + "{\\1c" + ass_color(style.color) + "}"

        text = re.sub(r"\S+", color_word, text)
    return text.replace("\n", "\\N")


def write_captions(path, segments, size):
    style = video_caption_style(segments[0].content.video) if segments else resolve_style("CLASSIC")
    header = ass_header(style, size)
    tracks = {track["id"]: track for track in voice_tracks(segments)} if any(
        segment.content.audio_settings.get("crossfade") for segment in segments
    ) else {}
    lines = []
    for segment in segments:
        scene = segment.content
        track = tracks.get(str(scene.pk))
        offset = track["start"] - scene.audio_settings.get("delay", 0) if track else segment.start
        for cue in scene_cues(scene, offset=offset, duration=segment.narration_duration, highlight=True):
            text = caption_ass_text(cue, style=style)
            scale = style.text_scale(cue.text, size)
            if scale < 1:
                percent = round(scale * 100, 3)
                text = "{\\fscx" + str(percent) + "\\fscy" + str(percent) + "}" + text
            lines.append(f"Dialogue: 0,{ass_timestamp(cue.start)},{ass_timestamp(cue.end)},Default,,0,0,0,,{text}")
    Path(path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
