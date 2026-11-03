"""Render educational diagram primitives with libass, without paid generation."""

import math

from ..diagrams import diagram_plan
from .ass import ass_color, ass_event, escape_ass_text

SHAPES = {
    "rect": "m 0 0 l {w:g} 0 {w:g} {h:g} 0 {h:g}",
    "arrow": "m 0 0 l {w:g} 0 {half:g} {h:g}",
}


def element_positions(element, start, end):
    """Repeat moving markers without resetting speed in the final partial cycle."""
    begin = start + element["start"]
    x, y = element["x"], element["y"]
    motion = element.get("motion")
    if motion is None:
        if begin < end:
            yield begin, end, f"\\pos({x:g},{y:g})"
        return
    period = motion["period"]
    for cycle in range(max(0, math.ceil((end - begin) / period))):
        event_start = begin + cycle * period
        yield event_start, min(end, event_start + period), (
            f"\\move({x:g},{y:g},{x:g},{motion['to_y']:g},0,{period * 1000:g})"
        )


def diagram_overlays(item, name, size, start, end):
    styles, events = [], []
    for index, element in enumerate(diagram_plan(item["diagram"], size, end - start)):
        event_start = start + element["start"]
        if event_start >= end:
            continue
        style_name = f"{name}_{index}"
        styles.append({"Name": style_name, "Fontname": "Poppins",
                       "Fontsize": element.get("size", 1), "Bold": -1,
                       "PrimaryColour": ass_color(element["color"], item["opacity"]),
                       "Outline": 0, "Shadow": 0, "Alignment": 7})
        fade = element["reveal"] * 1000
        tags = r"\bord0\shad0"
        if element["kind"] in SHAPES:
            if element.get("grow"):
                tags += f"\\fscx0\\t(0,{fade:g},\\fscx100)"
            w, h = element["width"], element["height"]
            content = SHAPES[element["kind"]].format(w=w, h=h, half=w / 2)
            tags += "\\p1"
        else:
            tags += f"\\fad({fade:g},0)"
            content = escape_ass_text(element["text"]).replace("\n", r"\N")
        for event_start, event_end, position in element_positions(element, start, end):
            events.append(ass_event(event_start, event_end, f"{{\\an7{position}{tags}}}{content}", style_name))
    return styles, events
