"""Render educational diagram primitives with libass, without paid generation."""

from ..diagrams import diagram_plan
from .ass import ass_color, ass_event, escape_ass_text


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
        tags = f"\\an7\\pos({element['x']:g},{element['y']:g})\\bord0\\shad0"
        if element["kind"] == "rect":
            if element["grow"]:
                tags += f"\\fscx0\\t(0,{fade:g},\\fscx100)"
            w, h = element["width"], element["height"]
            content = f"m 0 0 l {w:g} 0 {w:g} {h:g} 0 {h:g}"
            tags += "\\p1"
        else:
            tags += f"\\fad({fade:g},0)"
            content = escape_ass_text(element["text"]).replace("\n", r"\N")
        events.append(ass_event(event_start, end, f"{{{tags}}}{content}", style_name))
    return styles, events
