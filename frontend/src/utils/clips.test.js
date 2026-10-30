import { describe, expect, it, vi } from "vitest";
import { wordsForClip, validateClip, projectBusy, clipBusy, clipStalled } from "./clips";
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
  it("keeps rounded caption ends within decimal AI clip ranges", () => {
    const [word] = wordsForClip([{ text: "Excerpt", start: 149.34, end: 200.44 }], 149.34, 200.44);
    expect(word.end).toBeLessThanOrEqual(200.44 - 149.34);
    expect(word.end).toBeCloseTo(51.1, 9);
  });
  it("recognizes processing stages and creation navigation", () => {
    expect(projectBusy("ANALYZING")).toBe(true);
    expect(projectBusy("FAILED")).toBe(false);
    expect(clipBusy("RENDERING")).toBe(true);
    expect(isCreationPath("/clips/project-id/")).toBe(true);
  });
  it("uses the revision timestamp to detect an export that stalls after loading", () => {
    const now = Date.parse("2026-10-30T12:00:00Z");
    const clock = vi.spyOn(Date, "now").mockReturnValue(now);
    try {
      const clip = { status: "RENDERING", can_retry: false, revision: "2026-10-30T11:45:00Z" };
      expect(clipStalled(clip)).toBe(false);
      clock.mockReturnValue(now + 15 * 60000);
      expect(clipStalled(clip)).toBe(true);
      expect(clipStalled({ ...clip, status: "COMPLETED" })).toBe(false);
      expect(clipStalled({ ...clip, can_retry: true })).toBe(true);
    } finally {
      clock.mockRestore();
    }
  });
});

it("loads only changed clips and fetches the full transcript once it becomes available", async () => {
  const { reconcileClipProgress } = await import("./clips");
  const { vi } = await import("vitest");
  const old = { id: "p", words: [{ text: "Saved" }], clips: [{ id: "a", revision: "1", words: ["saved words"] }] };
  const loadProject = vi.fn();
  const loadClip = vi.fn().mockResolvedValue({ ok: true, data: { id: "b", revision: "2" } });
  const result = await reconcileClipProgress(old, { id: "p", has_transcript: true, clips: [{ id: "a", revision: "1", status: "READY" }, { id: "b", revision: "2" }] }, { loadProject, loadClip });
  expect(loadProject).not.toHaveBeenCalled();
  expect(loadClip).toHaveBeenCalledExactlyOnceWith("b");
  expect(result.clips[0].words).toEqual(["saved words"]);
  loadProject.mockResolvedValue({ ok: true, data: old });
  await reconcileClipProgress({ ...old, words: [] }, { id: "p", has_transcript: true, clips: [] }, { loadProject, loadClip });
  expect(loadProject).toHaveBeenCalledTimes(1);
});
