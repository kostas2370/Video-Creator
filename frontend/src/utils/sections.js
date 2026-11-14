// Source intervals shared by scene, full-video, and clip editing.
export const sectionsDuration = sections => sections.reduce((total, s) => total + s.end - s.start, 0);

export function segmentAt(segments, time) {
  let offset = 0;
  for (let index = 0; index < segments.length; index++) {
    const segment = segments[index];
    if (time < offset + segment.end - segment.start - 0.000001 || index === segments.length - 1) return { index, offset, source: Math.min(segment.end, segment.start + Math.max(0, time - offset)) };
    offset += segment.end - segment.start;
  }
}

export function splitSections(sections, time) {
  const duration = sectionsDuration(sections);
  if (!sections.length || !Number.isFinite(time) || !Number.isFinite(duration) || time < 0 || time > duration) return null;
  const { index, source } = segmentAt(sections, time);
  const section = sections[index];
  if (sections.length >= 100 || source - section.start < 0.05 || section.end - source < 0.05) return null;
  return [...sections.slice(0, index), { start: section.start, end: source }, { start: source, end: section.end }, ...sections.slice(index + 1)];
}

export const removeSection = (sections, index) => sections.length > 1 && sections[index] ? sections.filter((_, i) => i !== index) : null;

export function continuousSections(sections) {
  const result = [];
  for (const section of sections) {
    if (result.length && Math.abs(result[result.length - 1].end - section.start) < 1e-9) result[result.length - 1].end = section.end;
    else result.push({ ...section });
  }
  return result;
}
