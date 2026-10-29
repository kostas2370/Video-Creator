import { describe, expect, it } from "vitest";
import { wordsForClip, validateClip, projectBusy, clipBusy } from "./clips";
import { isCreationPath } from "./creationModes";

describe("clipping", () => {
  it("rebases overlapping caption words to clip-relative time", () => {
    const words = [{ text: "before", start: 0, end: 1 }, { text: "first", start: 2, end: 3 }, { text: "last", start: 4, end: 5 }, { text: "after", start: 6, end: 7 }];
    expect(wordsForClip(words, 2.5, 4.5)).toEqual([{ text: "first", start: 0, end: 0.5 }, { text: "last", start: 1.5, end: 2 }]);
    expect(words[1].start).toBe(2);
  });
  it("rejects out-of-source, reversed, nonfinite and oversized clips", () => {
    expect(validateClip(10, 70, 120)).toBe("");
    for (const [start, end] of [[-1, 2], [3, 2], [0, 201], [0, NaN], [Infinity, 20]]) expect(validateClip(start, end, 200)).not.toBe("");
  });
  it("recognizes processing stages and creation navigation", () => {
    expect(projectBusy("ANALYZING")).toBe(true);
    expect(projectBusy("FAILED")).toBe(false);
    expect(clipBusy("RENDERING")).toBe(true);
    expect(isCreationPath("/clips/project-id/")).toBe(true);
  });
});
