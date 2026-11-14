import { describe, expect, it } from "vitest";
import { videoLibraryInfo } from "./videoLibrary";

describe("video library presentation", () => {
  it("identifies manual, story, and AI projects", () => {
    expect(videoLibraryInfo({ video_type: "MANUAL" }).mode).toBe("Manual edit");
    expect(videoLibraryInfo({ video_type: "MANUAL", settings: { creation_mode: "STORY" } }).mode).toBe("Story video");
    expect(videoLibraryInfo({ video_type: "AI" }).mode).toBe("AI video");
  });
  it("uses actionable status labels and protects processing projects", () => {
    expect(videoLibraryInfo({ status: "REVIEW" }).label).toBe("Review script");
    expect(videoLibraryInfo({ status: "FAILED" }).label).toBe("Needs attention");
    for (const status of ["GENERATION", "RENDERING"]) {
      expect(videoLibraryInfo({ status })).toMatchObject({ processing: true, canDelete: false, canResume: false });
    }
  });
  it("offers retry only for AI projects with recoverable generation state", () => {
    const failed = { status: "FAILED", video_type: "AI", gpt_answer: { title: "Story" }, dir_name: "media/story" };
    expect(videoLibraryInfo(failed).canResume).toBe(true);
    expect(videoLibraryInfo({ ...failed, video_type: "MANUAL" }).canResume).toBe(false);
    expect(videoLibraryInfo({ ...failed, gpt_answer: null }).canResume).toBe(false);
    expect(videoLibraryInfo({ ...failed, dir_name: "" }).canResume).toBe(false);
  });
});


it("sends failed exports to the editor rather than offering AI generation resume", () => {
  expect(videoLibraryInfo({ status: "FAILED", video_type: "AI", gpt_answer: {}, dir_name: "media", render_error: { message: "Export failed" } }).canResume).toBe(false);
});


import { libraryProgress, libraryEmptyState } from "./videoLibrary";
it("reports saved assets without inventing export percentages", () => {
  expect(libraryProgress({ status: "GENERATION", scenes: [
    { scene_image: { file: "fox.png" }, narration_status: "available" },
    { narration_status: "missing" },
  ] }).steps).toEqual([
    { label: "Visuals prepared", done: 1, total: 2 },
    { label: "Narration prepared", done: 1, total: 2 },
  ]);
  expect(libraryProgress({ status: "RENDERING" }).steps).toEqual([]);
  expect(libraryProgress({ status: "GENERATION", scenes: [{ narration_status: "disabled" }] }).steps).toHaveLength(1);
});
it("explains favorites and combinations of empty-result constraints", () => {
  expect(libraryEmptyState({ is_favorite: true }).title).toBe("No favorites yet");
  const empty = libraryEmptyState({ search: "fox", status: "READY", creation_mode: "STORY", is_favorite: true });
  for (const text of ["fox", "Ready to export", "Story videos", "Favorites"]) expect(empty.description).toContain(text);
  expect(empty.action).toBe("Reset filters");
  expect(libraryEmptyState({}).action).toBeUndefined();
});
