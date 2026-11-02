"""Bounded, deterministic photo animation timelines. Coordinates are frame fractions.

The preview receives this exact camera/effect plan. The scene editor implements
the same preset builder in frontend/src/utils/photoAnimation.js for unsaved edits.
"""

from .motion import AMOUNTS


# (time, zoom amount, horizontal travel); each scene varies the same timeline.
CAMERA_FRAMES = {
    "PLAYFUL": [(0, 0, 0), (.12, 1, 0), (.22, .6, 0), (.58, .6, 0), (.7, 1.2, 0), (1, .8, 0)],
    "DRAMATIC": [(0, 0, 0), (.7, .4, 0), (1, 1.5, 0)],
    "CALM": [(0, 1, -.2), (1, 1, .2)],
    "EXPLAINER": [(0, 0, 0), (.18, 1, 0), (.75, 1, 0), (1, 0, 0)],
}
# (colors, vertical travel, size, opacity). Explainer has no particles.
PARTICLES = {
    "PLAYFUL": (["#facc15", "#38bdf8", "#f472b6"], .08, .005, .65),
    "DRAMATIC": (["#fbbf24"], -.05, .0025, .35),
    "CALM": (["#ffffff"], -.05, .0025, .35),
}


def animation_plan(scene):
    preset = getattr(scene, "animation_preset", "NONE")
    if preset not in CAMERA_FRAMES:
        return None
    seed = scene.pk.int % 997
    amount = AMOUNTS.get(scene.motion_intensity, 0.06) * (0.85 + seed % 3 * 0.15)
    direction = 1 if seed % 2 else -1
    camera = [
        {"at": at, "scale": 1 + amount * zoom, "x": direction * amount * x, "y": 0}
        for at, zoom, x in CAMERA_FRAMES[preset]
    ]
    particles = []
    if getattr(scene, "animation_accents", True) and preset in PARTICLES:
        colors, travel, size, opacity = PARTICLES[preset]
        for i in range(12):
            x = ((seed + i * 83) % 900 + 50) / 1000
            y = ((seed * 7 + i * 137) % 900 + 50) / 1000
            particles.append({
                "x": x, "y": y, "to_x": x + direction * .025, "to_y": y + travel,
                "size": size * (1 + i % 3 * .3), "color": colors[i % len(colors)],
                "opacity": opacity,
            })
    return {"preset": preset, "camera": camera, "particles": particles}


def keyframe_expression(frames, field, progress):
    """Compile linear keyframes to a bounded FFmpeg expression."""
    if all(frame[field] == frames[0][field] for frame in frames):
        return str(frames[0][field])
    expression = str(frames[-1][field])
    for left, right in reversed(list(zip(frames, frames[1:]))):
        value = (f"{left[field]}+({right[field]}-{left[field]})*"
                 f"(({progress})-{left['at']})/({right['at']}-{left['at']})")
        expression = f"if(lt({progress},{right['at']}),{value},{expression})"
    return expression
