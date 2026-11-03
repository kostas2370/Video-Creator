"""Deterministic diagram geometry shared with the browser through parity fixtures."""

import math

from .overlay_text import wrap_text

TEMPLATES = {
    "comparison": {"inset": .12, "markers": False, "rail": False},
    "timeline": {"inset": .22, "markers": True, "rail": True},
    "steps": {"inset": .22, "markers": True, "rail": False},
    "flow": {"inset": .22, "markers": True, "rail": False, "flow": True},
}
WIDE_GLYPHS = set("WMwm@%")
COLORS = ("#38bdf8", "#fbbf24", "#a78bfa", "#34d399")


def full_scene_diagram(scene):
    return any(item.get("kind") == "diagram" and item.get("start", 0) == 0
               and item.get("end") is None and item.get("opacity", 1) == 1
               for item in scene.overlays or [])


def diagram_plan(diagram, size, duration):
    """Lay out cards in the caption-safe region; reveal each over the scene."""
    width, height = size
    config = TEMPLATES[diagram["template"]]
    items = diagram["items"]
    row_height = height * .51 / len(items)
    reveal = min(.35, duration * .08)
    elements = []

    def rect(x, y, w, h, color, start=0, grow=False):
        elements.append(dict(kind="rect", x=x, y=y, width=w, height=h,
                             color=color, start=start, grow=grow, reveal=reveal))

    def text(value, x, y, max_width, font_size, max_height, color, start=0):
        # Conservative character widths also handle long words without clipping.
        columns = max(1, math.floor(max_width / (font_size * .7)))
        wrapped = wrap_text(" ".join(value.split()), 1, len, max_width=columns)
        lines = wrapped.split("\n")
        elements.append(dict(kind="text", x=x, y=y, text=wrapped,
                             size=min(font_size, max_height / (len(lines) * 1.3),
                                      max_width / max(1, max(sum(1.05 if char in WIDE_GLYPHS or ord(char) >= 0x2e80 else .65 for char in line) for line in lines))),
                             color=color, start=start, reveal=reveal))

    rect(0, 0, width, height, "#0f172a")
    text(diagram.get("title", ""), width * .1, height * .11, width * .8,
         min(width * .065, height * .065), height * .12, "#ffffff")
    if config["rail"]:
        rect(width * .135, height * .29, width * .004,
             row_height * (len(items) - 1), "#475569")
    for index, item in enumerate(items):
        y = height * .27 + index * row_height
        start = 0 if config.get("flow") else duration * .65 * index / max(1, len(items) - 1)
        color = COLORS[index]
        x = width * config["inset"]
        card_width = width * (.9 - config["inset"])
        rect(x - width * .025, y - row_height * .07, card_width + width * .025,
             row_height * .87, "#1e293b", start)
        rect(x, y, card_width * .92, max(2, height * .004), color, start, True)
        font = min(width * .055, row_height * .23)
        text(item["label"], x, y + row_height * .08, card_width * .92,
             font, row_height * .28, color, start)
        text(item.get("detail", ""), x, y + row_height * .38, card_width * .92,
             font * .8, row_height * .35, "#ffffff", start)
        if config["markers"]:
            edge = min(width * .06, row_height * .28)
            rect(width * .137 - edge / 2, y, edge, edge, color, start)
            text(str(index + 1), width * .137 - edge * .22, y + edge * .08,
                 edge * .6, edge * .6, edge, "#0f172a", start)
            if config.get("flow") and index < len(items) - 1:
                top = y + edge + height * .008
                bottom = y + row_height - height * .012
                head = min(width * .035, row_height * .1)
                center = width * .137
                rect(center - width * .003, top, width * .006, bottom - top - head, color)
                elements.append(dict(kind="arrow", x=center - head / 2, y=bottom - head,
                                     width=head, height=head, color=color, start=0, reveal=reveal))
                period = max(.001, min(1.4, duration * .24))
                dot = min(width * .018, head * .65)
                rect(center - dot / 2, top, dot, dot, "#ffffff", index * period / 3)
                elements[-1]["motion"] = {"to_y": bottom - head - dot, "period": period}
    return elements
