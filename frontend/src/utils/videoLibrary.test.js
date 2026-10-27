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
