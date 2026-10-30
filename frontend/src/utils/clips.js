export const projectBusy = status => ["QUEUED", "DOWNLOADING", "TRANSCRIBING", "ANALYZING"].includes(status);
export const clipBusy = status => ["QUEUED", "RENDERING"].includes(status);
export const clipStatus = { READY: "Ready to edit", QUEUED: "Export queued", RENDERING: "Exporting…", COMPLETED: "Export ready", FAILED: "Export needs attention" };
export const projectStatus = { QUEUED: "Waiting to process", DOWNLOADING: "Downloading YouTube video…", TRANSCRIBING: "Preparing video and transcribing speech…", ANALYZING: "Finding complete, interesting moments…", READY: "Ready to review", FAILED: "Needs attention" };
export const formatTime = value => {
  const seconds = Math.max(0, Math.floor(value || 0));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
};
export const wordsForClip = (words, start, end) => words.filter(word => word.end > start && word.start < end).map(word => ({ text: word.text, start: Number((Math.max(start, word.start) - start).toFixed(4)), end: Number((Math.min(end, word.end) - start).toFixed(4)) }));
export function validateClip(start, end, duration) {
  return Number.isFinite(start) && Number.isFinite(end) && start >= 0 && end <= duration && end > start && end - start <= 180 ? "" : "Choose a clip within the source video, up to 180 seconds long.";
}

export const clipStalled = clip => clip.can_retry || (clipBusy(clip.status) && Date.now() - new Date(clip.updated_at).getTime() >= 30 * 60000);

export async function reconcileClipProgress(current, progress, { loadProject, loadClip }) {
  if (!current || current.id !== progress.id || (progress.has_transcript && !current.words?.length)) {
    const result = await loadProject();
    if (!result.ok) throw new Error(result.message);
    return result.data;
  }
  const known = new Map(current.clips.map(clip => [clip.id, clip]));
  const clips = await Promise.all(progress.clips.map(async summary => {
    const clip = known.get(summary.id);
    if (clip && clip.revision === summary.revision) return { ...clip, ...summary };
    const result = await loadClip(summary.id);
    if (!result.ok) throw new Error(result.message);
    return result.data;
  }));
  return { ...current, ...progress, clips };
}
