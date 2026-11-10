import { segmentAt } from "./sections";
export { sectionsDuration } from "./sections";

export const sourcePosition = (sections, position) => sections.length ? segmentAt(sections, position).source : 0;
export function joinedPosition(sections, source) {
  let offset = 0;
  for (const section of sections) {
    if (source < section.end) return offset + Math.max(0, source - section.start);
    offset += section.end - section.start;
  }
  return offset;
}
export function previewSections(manifest, scene, override) {
  if (!manifest) return [];
  if (scene && override) return override.map(s => ({ start: scene.start + s.start, end: scene.start + s.end }));
  if (!scene && override && manifest.cut_source) return mapSections(manifest.cut_source.sections, override);
  const sections = (scene ? manifest.cut_source?.sections : null) || manifest.playback_sections || [{ start: 0, end: manifest.duration }];
  return scene ? sections.map(s => ({ start: Math.max(s.start, scene.start), end: Math.min(s.end, scene.start + scene.duration) })).filter(s => s.end > s.start) : sections;
}

export function cutClock(value) {
  const hundredths = Math.round(Math.max(0, value) * 100);
  return `${String(Math.floor(hundredths / 6000)).padStart(2, "0")}:${String(Math.floor(hundredths / 100) % 60).padStart(2, "0")}.${String(hundredths % 100).padStart(2, "0")}`;
}


export function mapSections(source, sections) {
  let offset = 0;
  return source.flatMap(part => {
    const length = part.end - part.start;
    const result = sections.map(section => ({ start: Math.max(offset, section.start), end: Math.min(offset + length, section.end) }))
      .filter(section => section.end > section.start)
      .map(section => ({ start: part.start + section.start - offset, end: part.start + section.end - offset }));
    offset += length;
    return result;
  });
}
