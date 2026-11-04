"""Shared image placement for watermark logos and local diagram artwork."""


def image_overlay(graph, stream, path, *, scale, position, timing, opacity):
    index = graph.input(path, ("-loop", "1", "-framerate", "24"))
    image = graph.filter([f"{index}:v"], f"{scale},format=rgba,colorchannelmixer=aa={opacity}")
    start, end = timing
    x, y = position
    return graph.filter(
        [stream, image],
        f"overlay=x={x}:y={y}:enable='gte(t,{start})*lt(t,{end})':eof_action=pass:shortest=0",
    )
