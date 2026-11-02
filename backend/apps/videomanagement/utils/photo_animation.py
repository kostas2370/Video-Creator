"""Bounded, deterministic photo animation timelines. Coordinates are frame fractions.

The preview receives this exact camera/effect plan. The scene editor implements
the same preset builder in frontend/src/utils/photoAnimation.js for unsaved edits.
"""

from .motion import AMOUNTS


def animation_plan(scene):
    preset = getattr(scene, "animation_preset", "NONE")
    if preset == "NONE":
        return None
    seed = scene.pk.int % 997
    amount = AMOUNTS.get(scene.motion_intensity, 0.06) * (0.85 + seed % 3 * 0.15)
    direction = 1 if seed % 2 else -1

    def frame(at, scale, x=0, y=0):
        return {"at": at, "scale": scale, "x": x, "y": y}

    if preset == "PLAYFUL":
        camera = [frame(0, 1), frame(0.12, 1 + amount),
                  frame(0.22, 1 + amount * 0.6), frame(0.58, 1 + amount * 0.6),
                  frame(0.7, 1 + amount * 1.2), frame(1, 1 + amount * 0.8)]
    elif preset == "DRAMATIC":
        camera = [frame(0, 1), frame(0.7, 1 + amount * 0.4),
                  frame(1, 1 + amount * 1.5)]
    elif preset == "CALM":
        camera = [frame(0, 1 + amount, -direction * amount * 0.2),
                  frame(1, 1 + amount, direction * amount * 0.2)]
    elif preset == "EXPLAINER":
        camera = [frame(0, 1), frame(0.18, 1 + amount),
                  frame(0.75, 1 + amount), frame(1, 1)]
    else:
        return None
    particles = []
    if getattr(scene, "animation_accents", True) and preset != "EXPLAINER":
        colors = {"PLAYFUL": ["#facc15", "#38bdf8", "#f472b6"],
                  "DRAMATIC": ["#fbbf24"], "CALM": ["#ffffff"]}[preset]
        for i in range(12):
            x = ((seed + i * 83) % 900 + 50) / 1000
            y = ((seed * 7 + i * 137) % 900 + 50) / 1000
            particles.append({
                "x": x, "y": y,
                "to_x": x + direction * 0.025,
                "to_y": y + (0.08 if preset == "PLAYFUL" else -0.05),
                "size": (0.005 if preset == "PLAYFUL" else 0.0025) * (1 + i % 3 * 0.3),
                "color": colors[i % len(colors)],
                "opacity": 0.65 if preset == "PLAYFUL" else 0.35,
            })
    return {"preset": preset, "camera": camera, "particles": particles}


def keyframe_expression(frames, field, progress):
    """Compile linear keyframes to a bounded FFmpeg expression."""
    expression = str(frames[-1][field])
    for left, right in reversed(list(zip(frames, frames[1:]))):
        value = (f"{left[field]}+({right[field]}-{left[field]})*"
                 f"(({progress})-{left['at']})/({right['at']}-{left['at']})")
        expression = f"if(lt({progress},{right['at']}),{value},{expression})"
    return expression
