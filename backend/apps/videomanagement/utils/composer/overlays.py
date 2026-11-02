"""Compose timed scene logos and text over the rendered picture."""

import math
from pathlib import Path

from django.conf import settings

from apps.videomanagement.exceptions import RenderFailedException
from apps.videomanagement.export_settings import export_settings

from ..file_utils import stored_file_exists
from ..fonts import subtitles_filter
from ..overlay_text import overlay_text_layout
from ..photo_animation import animation_plan
from .ass import ass_color, ass_event, escape_ass_text, write_document


# ASS templates use bounded entrance times, matching the preview's keyframes.
TEXT_ENTRANCES = {
    "PLAYFUL": (r"\pos({x},{y})\fscx70\fscy70"
                r"\t(0,{first:g},\fscx110\fscy110)"
                r"\t({first:g},{last:g},\fscx100\fscy100)"),
    "DRAMATIC": (r"\pos({x},{y})\fad({fade:g},0)\fscx115\fscy115"
                 r"\t(0,{settle:g},\fscx100\fscy100)"),
    "CALM": r"\pos({x},{y})\fad({settle:g},0)",
    "EXPLAINER": r"\move({x},{slide_y},{x},{y},0,{slide:g})\fad({slide:g},0)",
}


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
        raise RenderFailedException(
            "A watermark logo is missing. Upload it again before rendering."
        )
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
        "Name": name,
        "Fontname": font,
        "Fontsize": font_size,
        "PrimaryColour": color,
        "SecondaryColour": color,
        "OutlineColour": black,
        "BackColour": black,
        "Bold": -1,
        "BorderStyle": 3 if item["background"] else 1,
        "Outline": 6 if item["background"] else 1,
        "Alignment": alignment,
    }


def text_overlay(item, name, size, start, end, preset="NONE"):
    font = item.get("font") or settings.SUBTITLE_FONT
    wrapped, fitted_size = overlay_text_layout(
        escape_ass_text(item["text"]), item["size"], font, size
    )
    alignment, x, y = placement(item["position"], *size)
    style = text_style(item, name, font, size[0] * fitted_size / 100, alignment)
    safe = wrapped.replace("\n", "\\N")
    duration = (end - start) * 1000
    preset = "NONE" if item.get("kind") == "watermark" else preset
    template = TEXT_ENTRANCES.get(preset, r"\pos({x},{y})")
    position = template.format(
        x=x, y=y, slide_y=y + size[1] * .025,
        first=min(140, duration / 2), last=min(260, duration),
        fade=min(200, duration), settle=min(300, duration), slide=min(220, duration),
    )
    tags = f"\\an{alignment}{position}"
    text = f"{{{tags}}}{safe}"
    return style, ass_event(start, end, text, name)


def particle_overlays(segment, size, plan):
    """Vector accents share the preview's plan and hold still during scene pauses."""
    styles, events = [], []
    width, height = size
    # Match the last rendered camera frame, including 30fps exports.
    fps = export_settings(segment.content.video.settings or {})["fps"]
    travel = max(1, math.ceil(segment.base_duration * fps) - 1) / fps
    for i, particle in enumerate(plan["particles"]):
        name = f"Accent{segment.index}_{i}"
        styles.append({"Name": name, "PrimaryColour": ass_color(particle["color"], particle["opacity"]), "Outline": 0, "Shadow": 0, "Alignment": 7})
        x, y = particle["x"] * width, particle["y"] * height
        tx, ty = particle["to_x"] * width, particle["to_y"] * height
        edge = particle["size"] * width
        shape = f"m 0 0 l {edge:g} 0 {edge:g} {edge:g} 0 {edge:g}"
        tags = f"\\an7\\bord0\\shad0\\move({x},{y},{tx},{ty},0,{travel * 1000:g})\\p1"
        events.append(ass_event(segment.start, segment.start + segment.duration, f"{{{tags}}}{shape}", name))
    return styles, events


def apply_overlays(graph, stream, segments, size, directory):
    styles, events = [], []
    for segment in segments:
        plan = animation_plan(segment.content) if segment.visual_type == "image" else None
        if plan:
            accents, drawings = particle_overlays(segment, size, plan)
            styles.extend(accents)
            events.extend(drawings)
        for item in getattr(segment.content, "overlays", []):
            start = min(segment.duration, item["start"])
            end = min(
                segment.duration,
                item["end"] if item["end"] is not None else segment.duration,
            )
            if end <= start:
                continue
            start, end = start + segment.start, end + segment.start
            if item["logo"]:
                stream = add_logo(
                    graph, stream, segment.content, item, size, start, end
                )
            else:
                style, event = text_overlay(
                    item, f"Overlay{len(styles)}", size, start, end,
                    plan["preset"] if plan else "NONE",
                )
                styles.append(style)
                events.append(event)
    if styles:
        write_document(Path(directory, "overlays.ass"), size, styles, events)
        stream = graph.filter([stream], subtitles_filter("overlays.ass", directory))
    return stream
