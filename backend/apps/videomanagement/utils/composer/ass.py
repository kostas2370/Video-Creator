"""Shared ASS document primitives for captions and scene overlays."""
from pathlib import Path

ASS_STYLE_FIELDS = (
    "Name", "Fontname", "Fontsize", "PrimaryColour", "SecondaryColour", "OutlineColour",
    "BackColour", "Bold", "Italic", "Underline", "StrikeOut", "ScaleX", "ScaleY",
    "Spacing", "Angle", "BorderStyle", "Outline", "Shadow", "Alignment", "MarginL",
    "MarginR", "MarginV", "Encoding",
)
ASS_EVENT_FIELDS = "Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
STYLE_DEFAULTS = {
    "Name": "Default", "Fontname": "DejaVu Sans", "Fontsize": 48,
    "PrimaryColour": "&H00FFFFFF&", "SecondaryColour": "&H00FFFFFF&",
    "OutlineColour": "&H00000000&", "BackColour": "&H80000000&",
    "Bold": 0, "Italic": 0, "Underline": 0, "StrikeOut": 0, "ScaleX": 100,
    "ScaleY": 100, "Spacing": 0, "Angle": 0, "BorderStyle": 1, "Outline": 2,
    "Shadow": 0, "Alignment": 2, "MarginL": 0, "MarginR": 0, "MarginV": 0, "Encoding": 1,
}


def ass_timestamp(value):
    ticks = max(0, round(value * 100))
    return f"{ticks // 360000}:{ticks // 6000 % 60:02}:{ticks // 100 % 60:02}.{ticks % 100:02}"


def ass_color(color, opacity=1):
    alpha = round((1 - opacity) * 255)
    bgr = color[5:7] + color[3:5] + color[1:3]
    return f"&H{alpha:02X}{bgr.upper()}&"


def escape_ass_text(text):
    return text.replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\r", "")


def style_line(values):
    fields = {**STYLE_DEFAULTS, **values}
    fields["Fontname"] = fields["Fontname"].replace("-", " ").replace(",", " ").replace("\n", " ").replace("\r", " ")
    return "Style: " + ",".join(str(fields[field]) for field in ASS_STYLE_FIELDS)


def document_header(size, styles):
    return "\n".join([
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {size[0]}", f"PlayResY: {size[1]}",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "[V4+ Styles]",
        "Format: " + ", ".join(ASS_STYLE_FIELDS), *(style_line(style) for style in styles),
        "[Events]", "Format: " + ASS_EVENT_FIELDS, "",
    ])


def ass_event(start, end, text, style="Default"):
    return f"Dialogue: 0,{ass_timestamp(start)},{ass_timestamp(end)},{style},,0,0,0,,{text}"


def write_document(path, size, styles, events):
    Path(path).write_text(document_header(size, styles) + "\n".join(events) + "\n", encoding="utf-8")
