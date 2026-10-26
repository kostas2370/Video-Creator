export function shotAtTime(shots, time) {
  return shots.find(shot => time < shot.start + shot.duration) || shots[shots.length - 1];
}

export function shotDurations(shots, duration) {
  const total = shots.reduce((sum, shot) => sum + (shot.timing_weight || 1), 0);
  return shots.map(shot => duration * (shot.timing_weight || 1) / total);
}

export function moveShotBoundary(shots, index, seconds, duration) {
  const durations = shotDurations(shots, duration);
  const before = durations.slice(0, index).reduce((a, b) => a + b, 0);
  const pair = durations[index] + durations[index + 1];
  const minimum = Math.min(0.05, pair / 4);
  const left = Math.max(minimum, Math.min(pair - minimum, seconds - before));
  return shots.map((shot, i) => ({ ...shot, timing_weight: i === index ? left : i === index + 1 ? pair - left : durations[i] }));
}
