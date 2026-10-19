"""Compose timed scene logos and text over the rendered picture."""
from pathlib import Path

from django.conf import settings

from .ass import ass_color, ass_event, escape_ass_text, write_document
from ..exceptions import RenderFailedException
from ..file_utils import stored_file_exists
from ..fonts import subtitles_filter
from ..overlay_text import overlay_text_layout


def placement(position, width, height):
    vertical, horizontal = position.split("-")
    column = {"left": 0, "center": 1, "right": 2}[horizontal]
    row = {"bottom": 0, "middle": 1, "top": 2}[vertical]
    return (
        1 + column + row * 3,
        width * (0.05, 0.5, 0.95)[column],
        height * (0.95, 0.5, 0.05)[row],
    )


def add_logo(graph, stream, scene, item, size, start, end):
    field = scene.overlay_logo
    if not stored_file_exists(field):
        raise RenderFailedException("A watermark logo is missing. Upload it again before rendering.")
    alignment, x, y = placement(item["position"], *size)
    index = graph.input(field.path, ("-loop", "1", "-framerate", "24"))
    width = max(2, round(size[0] * item["width"] / 100))
    logo = graph.filter(
        [f"{index}:v"],
        f"scale={width}:{int(size[1] * 0.5)}:force_original_aspect_ratio=decrease,format=rgba,colorchannelmixer=aa={item['opacity']}",
    )
    column, row = (alignment - 1) % 3, (alignment - 1) // 3
    lx = f"{x}-overlay_w*{(0, 0.5, 1)[column]}"
    ly = f"{y}-overlay_h*{(1, 0.5, 0)[row]}"
    return graph.filter(
        [stream, logo],
        f"overlay=x={lx}:y={ly}:enable='gte(t,{start})*lt(t,{end})':eof_action=pass:shortest=0",
    )


def text_style(item, name, font, font_size, alignment):
    color = ass_color(item["color"], item["opacity"])
    black = ass_color("#000000", item["opacity"])
    return {
        "Name": name, "Fontname": font, "Fontsize": font_size,
        "PrimaryColour": color, "SecondaryColour": color,
        "OutlineColour": black, "BackColour": black, "Bold": -1,
        "BorderStyle": 3 if item["background"] else 1,
        "Outline": 6 if item["background"] else 1, "Alignment": alignment,
    }


def text_overlay(item, name, size, start, end):
    font = item.get("font") or settings.SUBTITLE_FONT
    wrapped, fitted_size = overlay_text_layout(escape_ass_text(item["text"]), item["size"], font, size)
    alignment, x, y = placement(item["position"], *size)
    style = text_style(item, name, font, size[0] * fitted_size / 100, alignment)
    safe = wrapped.replace("\n", "\\N")
    text = f"{{\\an{alignment}\\pos({x},{y})}}{safe}"
    return style, ass_event(start, end, text, name)


def apply_overlays(graph, stream, segments, size, directory):
    styles, events = [], []
    for segment in segments:
        for item in getattr(segment.content, "overlays", []):
            start = min(segment.duration, item["start"])
            end = min(segment.duration, item["end"] if item["end"] is not None else segment.duration)
            if end <= start:
                continue
            start, end = start + segment.start, end + segment.start
            if item["logo"]:
                stream = add_logo(graph, stream, segment.content, item, size, start, end)
            else:
                style, event = text_overlay(item, f"Overlay{len(styles)}", size, start, end)
                styles.append(style)
                events.append(event)
    if styles:
        write_document(Path(directory, "overlays.ass"), size, styles, events)
        stream = graph.filter([stream], subtitles_filter("overlays.ass", directory))
    return stream
