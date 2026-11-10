import { expect, it } from "vitest";
import { clipDuration, clipSegments, segmentAt, splitClip, removeClipSection } from "./clips";

it("splits at source time, removes the middle and rebases corrected captions", () => {
  const clip = { start: 10, end: 20, words: [{ text: "Corrected", start: 0, end: 1 }, { text: "Remove", start: 3, end: 4 }, { text: "Keep", start: 8, end: 9 }] };
  const split = splitClip(splitClip(clip, 2), 6);
  expect(split.words).toBe(clip.words);
  expect(clipSegments(split)).toEqual([{ start: 10, end: 12 }, { start: 12, end: 16 }, { start: 16, end: 20 }]);
  const cut = removeClipSection(split, 1);
  expect(clipDuration(cut)).toBe(6);
  expect(cut.words).toEqual([{ text: "Corrected", start: 0, end: 1 }, { text: "Keep", start: 4, end: 5 }]);
  expect(segmentAt(cut.segments, 2)).toEqual({ index: 1, offset: 2, source: 16 });
  expect(segmentAt(cut.segments, 6).source).toBe(20);
});

it("clips words crossing a removed section and prevents empty sections", () => {
  const clip = { start: 0, end: 4, words: [{ text: "Across", start: 0.5, end: 3.5 }] };
  const cut = removeClipSection(splitClip(splitClip(clip, 1), 3), 1);
  expect(cut.words).toEqual([{ text: "Across", start: 0.5, end: 1 }, { text: "Across", start: 1, end: 1.5 }]);
  expect(splitClip(clip, 0)).toBeNull();
  expect(splitClip(clip, 4)).toBeNull();
  expect(splitClip(clip, NaN)).toBeNull();
  expect(removeClipSection(clip, 0)).toBeNull();
});
