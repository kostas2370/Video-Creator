"""Run with: python manage.py shell < scripts/benchmark_renderers.py."""

import json
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import numpy as np
from PIL import Image
from moviepy.editor import ImageClip

from apps.videomanagement.utils.composer.ffmpeg import Graph, scene_visuals
from apps.videomanagement.utils.composer.layers import fit_to_canvas
from apps.videomanagement.utils.composer.motion import animate_image

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
        source = fit_to_canvas(ImageClip(str(path)).set_duration(duration), size)
        clip = animate_image(source, scene)
        start = time.perf_counter()
        clip.write_videofile(
            str(root / "moviepy.mp4"),
            fps=24,
            codec="libx264",
            preset="fast",
            ffmpeg_params=["-crf", "23"],
            threads=8,
            audio=False,
            logger=None,
        )
        moviepy_seconds = time.perf_counter() - start
        clip.close()
        source.close()
        graph = Graph()
        visual = scene_visuals(graph, [segment], size)
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
                "moviepy_seconds": round(moviepy_seconds, 3),
                "ffmpeg_seconds": round(native_seconds, 3),
                "speedup": round(moviepy_seconds / native_seconds, 2),
            }
        )
print(json.dumps(measurements, indent=2))
