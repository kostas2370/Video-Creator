"""Run with: python manage.py shell < scripts/benchmark_renderers.py."""

import json
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import numpy as np
from PIL import Image

from apps.videomanagement.utils.composer.render import Graph, visual_stream

size = (1920, 1080)
duration = 6
measurements = []
with tempfile.TemporaryDirectory(prefix="render-benchmark-") as directory:
    root = Path(directory)
    rng = np.random.default_rng(10)
    pixels = rng.integers(0, 256, (size[1], size[0], 3), dtype=np.uint8)
    path = root / "image.png"
    Image.fromarray(pixels).save(path)
    for style in ("ZOOM_IN", "PAN_RIGHT"):
        scene = SimpleNamespace(
            pk=UUID(int=5), motion_style=style, motion_intensity="MEDIUM"
        )
        image = SimpleNamespace(file=SimpleNamespace(path=str(path), name="image.png"))
        segment = SimpleNamespace(
            content=scene,
            image=image,
            kind="scene",
            visual_type="image",
            duration=duration,
            base_duration=duration,
            fade_in=0,
            fade_out=0,
            dissolve_in=0,
        )
        graph = Graph()
        visual = visual_stream(graph, segment, size)
        start = time.perf_counter()
        graph.run(
            root,
            root / "ffmpeg.mp4",
            [visual],
            ["-c:v", "libx264", "-preset", "fast", "-crf", "23", "-threads", "8"],
            duration,
        )
        native_seconds = time.perf_counter() - start
        measurements.append(
            {
                "motion": style,
                "seconds_of_video": duration,
                "size": size,
                "ffmpeg_seconds": round(native_seconds, 3),
                "render_fps": round(duration * 24 / native_seconds, 2),
            }
        )
print(json.dumps(measurements, indent=2))
