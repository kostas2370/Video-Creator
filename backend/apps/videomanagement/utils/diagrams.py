"""Deterministic diagram geometry shared with the browser through parity fixtures."""

import math

from .overlay_text import wrap_text

TEMPLATES = {
    "comparison": {"inset": .12, "markers": False, "rail": False, "max_items": 2},
    "timeline": {"inset": .22, "markers": True, "rail": True, "max_items": 4},
    "steps": {"inset": .22, "markers": True, "rail": False, "max_items": 4},
    "flow": {"inset": .22, "markers": True, "rail": False, "flow": True, "max_items": 4},
    "graph": {"graph": True, "max_items": 6},
}
WIDE_GLYPHS = set("WMwm@%")
COLORS = ("#38bdf8", "#fbbf24", "#a78bfa", "#34d399", "#fb7185", "#fb923c")


def graph_connections(diagram):
    return diagram.get("connections", [dict(source=i, target=i + 1, label="") for i in range(len(diagram["items"]) - 1)])


def graph_levels(count, connections):
    """Topological columns keep branches and merges ordered independently of item indices."""
    levels, incoming, outgoing = [0] * count, [0] * count, [[] for _ in range(count)]
    for edge in connections:
        source, target = edge["source"], edge["target"]
        if source == target or not (0 <= source < count and 0 <= target < count):
            raise ValueError("Connections must join two different existing items.")
        incoming[target] += 1
        outgoing[source].append(target)
    queue = [i for i, degree in enumerate(incoming) if degree == 0]
    processed = 0
    while queue:
        source = queue.pop(0)
        processed += 1
        for target in outgoing[source]:
            levels[target] = max(levels[target], levels[source] + 1)
            incoming[target] -= 1
            if incoming[target] == 0:
                queue.append(target)
    if processed != count:
        raise ValueError("Connections must not form a loop. Use branches or merges instead.")
    return levels


def motion_segments(element):
    """Return constant-speed legs for a moving marker, including routed graph connections."""
    motion = element["motion"]
    points = motion.get("path")
    if points is None:
        points = [(element["x"], element["y"]), (motion.get("to_x", element["x"]), motion["to_y"])]
    lengths = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:])]
    total = sum(lengths) or 1
    offset = 0
    for a, b, length in zip(points, points[1:], lengths):
        if length:
            duration = motion["period"] * length / total
            yield a, b, offset, duration
            offset += duration


def graph_plan(diagram, size, duration, elements, rect, text, place_icon):
    """Icon nodes and routed arrows, without the card presentation of other templates."""
    width, height = size
    connections = graph_connections(diagram)
    levels = graph_levels(len(diagram["items"]), connections)
    columns = max(levels) + 1
    node_width = min(width * .24, width * .76 / columns)
    groups = [[i for i, level in enumerate(levels) if level == column] for column in range(columns)]
    positions = {}
    for column, group in enumerate(groups):
        for row, index in enumerate(group):
            x = width * (.16 + .68 * column / max(1, columns - 1)) if columns > 1 else width * .5
            cell_height = height * .43 / len(group)
            y = height * .31 + cell_height * (row + .25)
            edge = min(node_width * .6, height * .12, cell_height * .32)
            positions[index] = (x, y, edge, cell_height)
    reveal = min(.35, duration * .08)
    period = max(.001, min(1.8, duration * .4))

    def polygon(points, color):
        left, top = min(x for x, _ in points), min(y for _, y in points)
        elements.append(dict(kind="polygon", x=left, y=top,
                             width=max(x for x, _ in points) - left, height=max(y for _, y in points) - top,
                             points=[[x - left, y - top] for x, y in points], color=color, start=0, reveal=reveal))

    for index, connection in enumerate(connections):
        source, target = connection["source"], connection["target"]
        sx, sy, se, _ = positions[source]
        tx, ty, te, _ = positions[target]
        x1, x2 = sx + se / 2 + width * .012, tx - te / 2 - width * .02
        head = min(width * .022, max(1, x2 - x1) * .2)
        color = COLORS[source]
        mid = (x1 + x2) / 2
        points = [[x1, sy], [mid, sy], [mid, ty], [x2 - head, ty]]
        if levels[target] - levels[source] > 1:
            lane = height * (.26 - index * .002)
            points = [[x1, sy], [x1 + width * .012, sy], [x1 + width * .012, lane],
                      [x2 - head - width * .012, lane], [x2 - head - width * .012, ty], [x2 - head, ty]]
        thickness = max(2, width * .004)
        for a, b in zip(points, points[1:]):
            distance = math.hypot(b[0] - a[0], b[1] - a[1])
            if not distance:
                continue
            dx, dy = -(b[1] - a[1]) / distance * thickness / 2, (b[0] - a[0]) / distance * thickness / 2
            polygon([[a[0]+dx, a[1]+dy], [b[0]+dx, b[1]+dy], [b[0]-dx, b[1]-dy], [a[0]-dx, a[1]-dy]], color)
        polygon([[x2-head, ty-head/2], [x2, ty], [x2-head, ty+head/2]], color)
        dot = min(width * .012, head * .65)
        path = [[x - dot / 2, y - dot / 2] for x, y in points]
        rect(*path[0], dot, dot, "#ffffff")
        elements[-1]["motion"] = {"path": path, "period": period}
        if connection.get("label"):
            text(connection["label"], x1, min(sy, ty) - height * .05, max(width * .06, x2 - x1),
                 width * .026, height * .04, "#cbd5e1")
    for index, item in enumerate(diagram["items"]):
        x, y, edge, cell_height = positions[index]
        if item.get("icon"):
            place_icon(item["icon"], x-edge/2, y-edge/2, edge)
        else:
            rect(x-edge/2, y-edge/2, edge, edge, COLORS[index])
        text(item["label"], x-node_width/2, y+edge/2+cell_height*.05, node_width,
             min(width*.042, node_width*.22, cell_height*.17), cell_height*.25, COLORS[index])
        elements[-1]["centered"] = node_width
        if item.get("detail"):
            text(item["detail"], x-node_width/2, y+edge/2+cell_height*.33, node_width,
                 min(width*.029, node_width*.17, cell_height*.13), cell_height*.25, "#ffffff")
            elements[-1]["centered"] = node_width
    return elements


def diagram_icon_keys(overlays):
    return {item["icon"] for overlay in overlays if overlay.get("kind") == "diagram"
            for item in overlay["diagram"]["items"] if item.get("icon")}


def full_scene_diagram(scene):
    return any(item.get("kind") == "diagram" and item.get("start", 0) == 0
               and item.get("end") is None and item.get("opacity", 1) == 1
               for item in scene.overlays or [])


def diagram_text_layout(value, max_width, font_size, max_height):
    """Fit wrapped labels conservatively, including wide and non-Latin glyphs."""
    columns = max(1, math.floor(max_width / (font_size * .7)))
    wrapped = wrap_text(" ".join(value.split()), 1, len, max_width=columns)
    lines = wrapped.split("\n")
    text_width = max(1, max(sum(
        1.05 if char in WIDE_GLYPHS or ord(char) >= 0x2e80 else .65
        for char in line
    ) for line in lines))
    size = min(font_size, max_height / (len(lines) * 1.3), max_width / text_width)
    return wrapped, size


def diagram_plan(diagram, size, duration):
    """Build shared primitives and delegate to the selected diagram layout."""
    width, height = size
    config = TEMPLATES[diagram["template"]]
    reveal = min(.35, duration * .08)
    elements = []

    def rect(x, y, w, h, color, start=0, grow=False):
        elements.append(dict(kind="rect", x=x, y=y, width=w, height=h,
                             color=color, start=start, grow=grow, reveal=reveal))

    def place_icon(identifier, x, y, edge, start=0):
        elements.append(dict(kind="icon", icon=identifier, x=x, y=y, width=edge,
                             height=edge, start=start, reveal=reveal))

    def text(value, x, y, max_width, font_size, max_height, color, start=0):
        wrapped, fitted_size = diagram_text_layout(value, max_width, font_size, max_height)
        elements.append(dict(kind="text", x=x, y=y, text=wrapped, size=fitted_size,
                             color=color, start=start, reveal=reveal))

    rect(0, 0, width, height, "#0f172a")
    text(diagram.get("title", ""), width * .1, height * .11, width * .8,
         min(width * .065, height * .065), height * .12, "#ffffff")
    if config.get("graph"):
        return graph_plan(diagram, size, duration, elements, rect, text, place_icon)
    return card_plan(diagram, size, duration, elements, rect, text, place_icon)


def card_plan(diagram, size, duration, elements, rect, text, place_icon):
    """Lay out comparison, timeline, step and flow cards using shared primitives."""
    width, height = size
    config = TEMPLATES[diagram["template"]]
    items = diagram["items"]
    row_height = height * .51 / len(items)
    reveal = min(.35, duration * .08)
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
        icon = item.get("icon")
        icon_edge = min(width * .075, row_height * .25) if icon else 0
        label_width = card_width * .92 - (icon_edge + width * .02 if icon else 0)
        if icon:
            place_icon(icon, x + card_width * .92 - icon_edge, y + row_height * .08, icon_edge, start)
        text(item["label"], x, y + row_height * .08, label_width,
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
