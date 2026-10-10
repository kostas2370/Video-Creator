export function formatDuration(seconds) {
  if (!Number.isFinite(seconds)) return "Pending";
  const tenths = Math.round(seconds * 10);
  const minutes = Math.floor(tenths / 600);
  const remainder = ((tenths % 600) / 10).toFixed(1);
  return minutes ? `${minutes}m ${remainder}s` : `${remainder}s`;
}
