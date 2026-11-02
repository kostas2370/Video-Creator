import { animationProgress, keyframeAt } from "./photoAnimation";

export function imageMotion(segment, time) {
  if (segment.photo_animation?.camera?.length) {
    const camera = keyframeAt(segment.photo_animation.camera, animationProgress(time, segment.base_duration, segment.fps));
    return { transform: `translate(${camera.x * 100}%, ${camera.y * 100}%) scale(${camera.scale})`, transformOrigin: "center" };
  }
  const end = Math.max(0, segment.base_duration - 1 / 24);
  const progress = end ? Math.min(1, Math.max(0, time / end)) : 1;
  const amount = { SUBTLE: 0.06, MEDIUM: 0.12, STRONG: 0.20 }[segment.motion_intensity] ?? 0.06;
  let scale = 1, x = 0, y = 0;
  const travel = amount * (progress - 0.5) * 100;
  switch (segment.motion_style) {
    case "ZOOM_IN": scale += amount * progress; break;
    case "ZOOM_OUT": scale += amount * (1 - progress); break;
    case "PAN_LEFT": scale += amount; x = -travel; break;
    case "PAN_RIGHT": scale += amount; x = travel; break;
    case "PAN_UP": scale += amount; y = -travel; break;
    case "PAN_DOWN": scale += amount; y = travel; break;
    default: break;
  }
  return { transform: `translate(${x}%, ${y}%) scale(${scale})`, transformOrigin: "center" };
}

export function resolveImageMotion(style, sceneId) {
  if (style !== "AUTO") return style;
  const movements = ["ZOOM_IN", "ZOOM_OUT", "PAN_LEFT", "PAN_RIGHT", "PAN_UP", "PAN_DOWN"];
  const identity = String(sceneId).replaceAll("-", "");
  return movements[Number(BigInt(`0x${identity}`) % 6n)];
}
