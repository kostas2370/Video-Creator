export const projectBusy = status => ["QUEUED", "TRANSCRIBING", "ANALYZING"].includes(status);
export const clipBusy = status => ["QUEUED", "RENDERING"].includes(status);
export const clipStatus = { READY: "Ready to edit", QUEUED: "Export queued", RENDERING: "Exporting…", COMPLETED: "Export ready", FAILED: "Export needs attention" };
export const projectStatus = { QUEUED: "Waiting to process", TRANSCRIBING: "Preparing video and transcribing speech…", ANALYZING: "Finding complete, interesting moments…", READY: "Ready to review", FAILED: "Needs attention" };
export const formatTime = value => {
  const seconds = Math.max(0, Math.floor(value || 0));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
};
export const wordsForClip = (words, start, end) => words.filter(word => word.end > start && word.start < end).map(word => ({ text: word.text, start: Number((Math.max(start, word.start) - start).toFixed(4)), end: Number((Math.min(end, word.end) - start).toFixed(4)) }));
export function validateClip(start, end, duration) {
  return Number.isFinite(start) && Number.isFinite(end) && start >= 0 && end <= duration && end > start && end - start <= 180 ? "" : "Choose a clip within the source video, up to 180 seconds long.";
}

export const clipStalled = clip => clipBusy(clip.status) && Date.now() - new Date(clip.updated_at).getTime() >= 3 * 3600000;
