// Keep the unsaved editor's preset builder in sync with utils/photo_animation.py.
export const photoPresets = [
  ["NONE", "Camera only", "Use the individual zoom and pan controls."],
  ["PLAYFUL", "Playful", "Punchy zooms, popping text, and colorful confetti."],
  ["DRAMATIC", "Dramatic", "An accelerating push in, bold text, and warm dust."],
  ["CALM", "Calm", "Gentle drifting, fading text, and soft floating specks."],
  ["EXPLAINER", "Explainer", "Zoom, hold, and pull back, with sliding labels."],
];

export function photoAnimationPlan(preset = "NONE", intensity = "SUBTLE", sceneId, accents = true) {
  if (preset === "NONE") return null;
  const identity = String(sceneId).replaceAll("-", "");
  const seed = /^[0-9a-f]+$/i.test(identity) ? Number(BigInt(`0x${identity}`) % 997n) : 0;
  const amount = ({ SUBTLE: 0.06, MEDIUM: 0.12, STRONG: 0.2 }[intensity] ?? 0.06) * (.85 + (seed % 3) * .15);
  const direction = seed % 2 ? 1 : -1;
  const frame = (at, scale, x = 0, y = 0) => ({ at, scale, x, y });
  let camera;
  if (preset === "PLAYFUL") camera = [frame(0, 1), frame(.12, 1 + amount), frame(.22, 1 + amount * .6), frame(.58, 1 + amount * .6), frame(.7, 1 + amount * 1.2), frame(1, 1 + amount * .8)];
  else if (preset === "DRAMATIC") camera = [frame(0, 1), frame(.7, 1 + amount * .4), frame(1, 1 + amount * 1.5)];
  else if (preset === "CALM") camera = [frame(0, 1 + amount, -direction * amount * .2), frame(1, 1 + amount, direction * amount * .2)];
  else if (preset === "EXPLAINER") camera = [frame(0, 1), frame(.18, 1 + amount), frame(.75, 1 + amount), frame(1, 1)];
  else return null;
  const particles = [];
  if (accents && preset !== "EXPLAINER") {
    const colors = { PLAYFUL: ["#facc15", "#38bdf8", "#f472b6"], DRAMATIC: ["#fbbf24"], CALM: ["#ffffff"] }[preset];
    for (let i = 0; i < 12; i++) {
      const x = ((seed + i * 83) % 900 + 50) / 1000;
      const y = ((seed * 7 + i * 137) % 900 + 50) / 1000;
      particles.push({ x, y, to_x: x + direction * .025, to_y: y + (preset === "PLAYFUL" ? .08 : -.05), size: (preset === "PLAYFUL" ? .005 : .0025) * (1 + i % 3 * .3), color: colors[i % colors.length], opacity: preset === "PLAYFUL" ? .65 : .35 });
    }
  }
  return { preset, camera, particles };
}

export function animationProgress(time, duration, fps = 24) {
  const last = Math.max(1, Math.ceil(duration * fps) - 1);
  return Math.min(1, Math.max(0, time * fps / last));
}

export function cameraAt(frames, progress) {
  const right = frames.findIndex(frame => frame.at > progress);
  if (right <= 0) return frames[right === 0 ? 0 : frames.length - 1];
  const a = frames[right - 1], b = frames[right];
  const fraction = (progress - a.at) / (b.at - a.at);
  return Object.fromEntries(["scale", "x", "y"].map(key => [key, a[key] + (b[key] - a[key]) * fraction]));
}

export function overlayEntrance(preset, time, duration) {
  const elapsed = Math.max(0, time);
  const entranceDuration = { PLAYFUL: .26, DRAMATIC: .3, CALM: .3, EXPLAINER: .22 }[preset] ?? 0;
  if (elapsed >= Math.min(entranceDuration, duration)) return { scale: 1, opacity: 1, dy: 0 };
  const progress = seconds => Math.min(1, elapsed / Math.max(.001, Math.min(seconds, duration)));
  if (preset === "PLAYFUL") {
    const a = Math.min(.14, duration / 2), b = Math.min(.26, duration);
    const scale = elapsed < a ? .7 + .4 * elapsed / Math.max(.001, a) : 1.1 - .1 * Math.min(1, (elapsed - a) / Math.max(.001, b - a));
    return { scale, opacity: 1, dy: 0 };
  }
  if (preset === "DRAMATIC") return { scale: 1.15 - .15 * progress(.3), opacity: progress(.2), dy: 0 };
  if (preset === "CALM") return { scale: 1, opacity: progress(.3), dy: 0 };
  if (preset === "EXPLAINER") return { scale: 1, opacity: progress(.22), dy: .025 * (1 - progress(.22)) };
  return { scale: 1, opacity: 1, dy: 0 };
}
