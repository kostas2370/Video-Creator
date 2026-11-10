export const projectBusy = status => ["QUEUED", "DOWNLOADING", "TRANSCRIBING", "ANALYZING"].includes(status);
export const clipBusy = status => ["QUEUED", "RENDERING"].includes(status);
export const clipStatus = { READY: "Ready to edit", QUEUED: "Export queued", RENDERING: "Exporting…", COMPLETED: "Export ready", FAILED: "Export needs attention" };
export const projectStatus = { QUEUED: "Waiting to process", DOWNLOADING: "Downloading YouTube video…", TRANSCRIBING: "Preparing video and transcribing speech…", ANALYZING: "Finding complete, interesting moments…", READY: "Ready to review", FAILED: "Needs attention" };
export const formatTime = value => {
  const seconds = Math.max(0, Math.floor(value || 0));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
};
export const minutesToSeconds = value => Number((Number(value) * 60).toFixed(6));
export const wordsForClip = (words, start, end) => words.filter(word => word.end > start && word.start < end).map(word => ({ text: word.text, start: Number((Math.max(start, word.start) - start).toFixed(4)), end: Math.min(end - start, Number((Math.min(end, word.end) - start).toFixed(4))) }));
export function validateClip(start, end, duration, minimum = 0) {
  return Number.isFinite(start) && Number.isFinite(end) && start >= minimum && end <= duration && end > start && end - start <= 180 ? "" : "Choose a clip within the source video, up to 180 seconds long.";
}

export const clipStalled = clip => clip.can_retry || (clipBusy(clip.status) && Date.now() - new Date(clip.revision).getTime() >= 30 * 60000);

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

// Segments use original source times; caption words use the joined output timeline.
export const clipSegments = clip => clip.segments?.length ? clip.segments : [{ start: clip.start, end: clip.end }];
export const clipDuration = clip => clipSegments(clip).reduce((total, s) => total + s.end - s.start, 0);
export function segmentAt(segments, time) {
  let offset = 0;
  for (let index = 0; index < segments.length; index++) {
    const segment = segments[index];
    if (time < offset + segment.end - segment.start - 0.000001 || index === segments.length - 1) return { index, offset, source: Math.min(segment.end, segment.start + Math.max(0, time - offset)) };
    offset += segment.end - segment.start;
  }
}
export function splitClip(clip, time) {
  if (!Number.isFinite(time) || !Number.isFinite(clipDuration(clip)) || time < 0 || time > clipDuration(clip)) return null;
  const segments = clipSegments(clip);
  const { index, source } = segmentAt(segments, time);
  const segment = segments[index];
  if (segments.length >= 100 || source - segment.start < 0.05 || segment.end - source < 0.05) return null;
  return { ...clip, segments: [...segments.slice(0, index), { start: segment.start, end: source }, { start: source, end: segment.end }, ...segments.slice(index + 1)] };
}
export function removeClipSection(clip, index) {
  const segments = clipSegments(clip);
  if (segments.length <= 1 || !segments[index]) return null;
  const start = segments.slice(0, index).reduce((total, s) => total + s.end - s.start, 0);
  const end = start + segments[index].end - segments[index].start;
  const duration = clipDuration(clip);
  const words = [
    ...wordsForClip(clip.words, 0, start),
    ...wordsForClip(clip.words, end, duration).map(word => ({ ...word, start: Number((word.start + start).toFixed(4)), end: Math.min(duration - (end - start), Number((word.end + start).toFixed(4))) })),
  ];
  return { ...clip, segments: segments.filter((_, i) => i !== index), words };
}
