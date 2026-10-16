"""Scene-local overlays, assembled after the presenter and before captions."""

from pathlib import Path

from django.conf import settings

from ..exceptions import RenderFailedException
from ..file_utils import stored_file_exists


def placement(position, width, height):
    vertical, horizontal = position.split("-")
    column = {"left": 0, "center": 1, "right": 2}[horizontal]
    row = {"bottom": 0, "middle": 1, "top": 2}[vertical]
    return (
        1 + column + row * 3,
        width * (0.05, 0.5, 0.95)[column],
        height * (0.95, 0.5, 0.05)[row],
    )


def timestamp(value):
    ticks = max(0, round(value * 100))
    return f"{ticks // 360000}:{ticks // 6000 % 60:02}:{ticks // 100 % 60:02}.{ticks % 100:02}"


def wrap_text(text, size):
    # Explicit breaks keep browser and export wrapping consistent at every format.
    columns = max(10, int(140 / size))
    paragraphs = []
    for line in text.split("\n"):
        lines, current = [], ""
        for word in line.split():
            if current and len(current) + len(word) + 1 > columns:
                lines.append(current)
                current = ""
            if current:
                current += " "
            while len(word) > columns:
                lines.append(word[:columns])
                word = word[columns:]
            current += word
        if current:
            lines.append(current)
        paragraphs.append("\n".join(lines))
    return "\n".join(paragraphs)


def apply_overlays(graph, stream, segments, size, directory):
    font = settings.SUBTITLE_FONT.replace("-", " ").replace(",", " ").replace("\n", " ")
    lines = []
    for segment in segments:
        for item in getattr(segment.content, "overlays", []):
            start = min(segment.duration, item["start"])
            end = min(
                segment.duration,
                item["end"] if item["end"] is not None else segment.duration,
            )
            if end <= start:
                continue
            start += segment.start
            end += segment.start
            alignment, x, y = placement(item["position"], *size)
            if item["logo"]:
                field = segment.content.overlay_logo
                if not stored_file_exists(field):
                    raise RenderFailedException(
                        "A watermark logo is missing. Upload it again before rendering."
                    )
                index = graph.input(field.path, ("-loop", "1", "-framerate", "24"))
                width = max(2, round(size[0] * item["width"] / 100))
                logo = graph.filter(
                    [f"{index}:v"],
                    f"scale={width}:{int(size[1] * 0.5)}:force_original_aspect_ratio=decrease,format=rgba,colorchannelmixer=aa={item['opacity']}",
                )
                column, row = (alignment - 1) % 3, (alignment - 1) // 3
                lx = f"{x}-overlay_w*{(0, 0.5, 1)[column]}"
                ly = f"{y}-overlay_h*{(1, 0.5, 0)[row]}"
                stream = graph.filter(
                    [stream, logo],
                    f"overlay=x={lx}:y={ly}:enable='gte(t,{start})*lt(t,{end})':eof_action=pass:shortest=0",
                )
                continue
            color = item["color"].lstrip("#")
            bgr = color[4:6] + color[2:4] + color[0:2]
            alpha = round((1 - item["opacity"]) * 255)
            border = 3 if item["background"] else 1
            # Separate styles allow each block its own opaque box and color.
            name = f"Overlay{len(lines)}"
            safe = (
                wrap_text(item["text"], item["size"])
                .replace("\\", "＼")
                .replace("{", "｛")
                .replace("}", "｝")
                .replace("\r", "")
                .replace("\n", "\\N")
            )
            lines.append(
                (
                    f"Style: {name},{font},{size[0] * item['size'] / 100},&H{alpha:02X}{bgr},&H{alpha:02X}{bgr},&H{alpha:02X}000000,&H{alpha:02X}000000,-1,0,0,0,100,100,0,0,{border},{6 if item['background'] else 1},0,{alignment},0,0,0,1",
                    f"Dialogue: 0,{timestamp(start)},{timestamp(end)},{name},,0,0,0,,{{\\an{alignment}\\pos({x},{y})}}{safe}",
                )
            )
    if lines:
        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {size[0]}
PlayResY: {size[1]}
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""
        events = "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        Path(directory, "overlays.ass").write_text(
            header
            + "\n".join(s for s, _ in lines)
            + events
            + "\n".join(e for _, e in lines)
            + "\n",
            encoding="utf-8",
        )
        stream = graph.filter([stream], "subtitles=filename=overlays.ass")
    return stream
