// Keep the unsaved editor's preset builder in sync with utils/photo_animation.py.
export const photoPresets = [
  ["NONE", "Camera only", "Use the individual zoom and pan controls."],
  ["PLAYFUL", "Playful", "Punchy zooms, popping text, and colorful confetti."],
  ["DRAMATIC", "Dramatic", "An accelerating push in, bold text, and warm dust."],
  ["CALM", "Calm", "Gentle drifting, fading text, and soft floating specks."],
  ["EXPLAINER", "Explainer", "Zoom, hold, and pull back, with sliding labels."],
];

// (time, zoom amount, horizontal travel); mirrors the render timeline tables.
const cameraFrames = {
  PLAYFUL: [[0, 0, 0], [.12, 1, 0], [.22, .6, 0], [.58, .6, 0], [.7, 1.2, 0], [1, .8, 0]],
  DRAMATIC: [[0, 0, 0], [.7, .4, 0], [1, 1.5, 0]],
  CALM: [[0, 1, -.2], [1, 1, .2]],
  EXPLAINER: [[0, 0, 0], [.18, 1, 0], [.75, 1, 0], [1, 0, 0]],
};
// (colors, vertical travel, size, opacity). Explainer has no particles.
const particleStyles = {
  PLAYFUL: [["#facc15", "#38bdf8", "#f472b6"], .08, .005, .65],
  DRAMATIC: [["#fbbf24"], -.05, .0025, .35],
  CALM: [["#ffffff"], -.05, .0025, .35],
};

export function photoAnimationPlan(preset = "NONE", intensity = "SUBTLE", sceneId, accents = true) {
  if (!cameraFrames[preset]) return null;
  const identity = String(sceneId).replaceAll("-", "");
  const seed = /^[0-9a-f]+$/i.test(identity) ? Number(BigInt(`0x${identity}`) % 997n) : 0;
  const amount = ({ SUBTLE: .06, MEDIUM: .12, STRONG: .2 }[intensity] ?? .06) * (.85 + (seed % 3) * .15);
  const direction = seed % 2 ? 1 : -1;
  const camera = cameraFrames[preset].map(([at, zoom, x]) => ({ at, scale: 1 + amount * zoom, x: x === 0 ? 0 : direction * amount * x, y: 0 }));
  const particles = [];
  if (accents && particleStyles[preset]) {
    const [colors, travel, size, opacity] = particleStyles[preset];
    for (let i = 0; i < 12; i++) {
      const x = ((seed + i * 83) % 900 + 50) / 1000;
      const y = ((seed * 7 + i * 137) % 900 + 50) / 1000;
      particles.push({ x, y, to_x: x + direction * .025, to_y: y + travel, size: size * (1 + i % 3 * .3), color: colors[i % colors.length], opacity });
    }
  }
  return { preset, camera, particles };
}

export function animationProgress(time, duration, fps = 24) {
  const last = Math.max(1, Math.ceil(duration * fps) - 1);
  return Math.min(1, Math.max(0, time * fps / last));
}

export function keyframeAt(frames, progress) {
  const right = frames.findIndex(frame => frame.at > progress);
  if (right <= 0) return frames[right === 0 ? 0 : frames.length - 1];
  const a = frames[right - 1], b = frames[right];
  const fraction = (progress - a.at) / (b.at - a.at);
  return Object.fromEntries(Object.keys(a).filter(key => key !== "at").map(key => [key, a[key] + (b[key] - a[key]) * fraction]));
}

// Each point is (seconds, maximum fraction of overlay duration, value).
const textEntrances = {
  PLAYFUL: { scale: [[0, 0, .7], [.14, .5, 1.1], [.26, 1, 1]] },
  DRAMATIC: { scale: [[0, 0, 1.15], [.3, 1, 1]], opacity: [[0, 0, 0], [.2, 1, 1]] },
  CALM: { opacity: [[0, 0, 0], [.3, 1, 1]] },
  EXPLAINER: { opacity: [[0, 0, 0], [.22, 1, 1]], dy: [[0, 0, .025], [.22, 1, 0]] },
};

export function overlayEntrance(preset, time, duration) {
  const result = { scale: 1, opacity: 1, dy: 0 };
  for (const [property, points] of Object.entries(textEntrances[preset] || {})) {
    const frames = points.map(([seconds, fraction, value]) => ({ at: Math.min(seconds, duration * fraction), value }));
    result[property] = keyframeAt(frames, Math.max(0, time)).value;
  }
  return result;
}
