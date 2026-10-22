import { describe, expect, it } from "vitest";
import { appendTimestamps, descriptionBytes, youtubeTags, youtubeTagLength } from "./youtubeMetadata";

describe("YouTube upload metadata", () => {
  it("normalizes keywords while preserving multiword phrases", () => {
    expect(youtubeTags(" ocean life, Ocean Life, whales\n marine animals ")).toEqual(["ocean life", "whales", "marine animals"]);
  });
  it("counts separators and implicit quotes in the YouTube tag limit", () => {
    expect(youtubeTagLength(["ocean life", "whales"])).toBe(19);
    expect(youtubeTagLength([])).toBe(0);
    expect(youtubeTagLength(["🐳"])).toBe(1);
  });
  it("counts UTF-8 bytes for multilingual descriptions", () => {
    expect(descriptionBytes("hello")).toBe(5);
    expect(descriptionBytes("🐳")).toBe(4);
  });
  it("replaces generated chapters when requested again without duplicating them", () => {
    const chapters = "Chapters\n00:00 Intro\n00:10 Whales\n00:25 Reefs";
    expect(appendTimestamps("Ocean life", chapters)).toBe(`Ocean life\n\n${chapters}`);
    expect(appendTimestamps(`Ocean life\n\n${chapters}`, chapters)).toBe(`Ocean life\n\n${chapters}`);
  });
});
