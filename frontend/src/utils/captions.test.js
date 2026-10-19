import { describe, expect, it } from "vitest";
import { captionAt, captionGroups, insertCaptionWord, validateCaptionWords } from "./captions";

const words = [{ text: "Hello", start: 0.1, end: 0.3 }, { text: "world.", start: 0.45, end: 0.8 }, { text: "Again", start: 1.5, end: 2 }];
describe("caption timing", () => {
  it("uses measured starts for highlights and hides captions during phrase gaps", () => {
    const groups = captionGroups(words);
    expect(captionAt(groups, 0.09)).toBeNull();
    expect(captionAt(groups, 0.1)).toEqual({ text: "Hello world.", active_word: 0 });
    expect(captionAt(groups, 0.4).active_word).toBe(0);
    expect(captionAt(groups, 0.45).active_word).toBe(1);
    expect(captionAt(groups, 0.8)).toBeNull();
    expect(captionAt(groups, 1.5).text).toBe("Again");
  });
  it("keeps short TikTok phrases and sentence-style classic captions", () => {
    const items = Array.from({ length: 8 }, (_, i) => ({ text: "one", start: i, end: i + 0.8 }));
    expect(captionGroups(items).map(group => group.length)).toEqual([4, 4]);
    expect(captionGroups(items, "CLASSIC")).toHaveLength(1);
    expect(captionAt(captionGroups(words, "CLASSIC"), 0.45, "CLASSIC").active_word).toBeNull();
  });
  it("rejects invalid edits before saving and preserves valid measured timing", () => {
    expect(validateCaptionWords(words, 2)).toBe("");
    expect(validateCaptionWords([{ text: "two words", start: 0, end: 1 }], 2)).toContain("one word");
    expect(validateCaptionWords([{ text: "Hi", start: NaN, end: 1 }], 2)).toContain("check");
    expect(validateCaptionWords([{ text: "Hi", start: 1, end: 3 }], 2)).toContain("check");
    expect(validateCaptionWords([{ text: "Hi", start: 0, end: 1 }, { text: "again", start: 0.9, end: 2 }], 2)).toContain("without overlapping");
  });
});


describe("caption word insertion", () => {
  it("inserts at a gap in the middle without shifting existing words", () => {
    const inserted = insertCaptionWord(words, 0.32, 2);
    expect(inserted.index).toBe(1);
    expect(inserted.words[1]).toEqual({ text: "", start: 0.32, end: 0.45 });
    expect(inserted.words[0]).toEqual(words[0]);
    expect(inserted.words[2]).toEqual(words[1]);
  });
  it("supports the beginning, the end, and an empty transcript", () => {
    expect(insertCaptionWord(words, 0, 2).index).toBe(0);
    expect(insertCaptionWord(words, 2, 3).words[3]).toEqual({ text: "", start: 2, end: 2.3 });
    expect(insertCaptionWord([], 0, 1).words).toEqual([{ text: "", start: 0, end: 0.3 }]);
  });
  it("rejects places without room or valid timing", () => {
    expect(insertCaptionWord([{ text: "Hello", start: 0, end: 2 }], 1, 2)).toBeNull();
    expect(insertCaptionWord(words, NaN, 2)).toBeNull();
    expect(insertCaptionWord(words, 2, 2)).toBeNull();
  });
});

it("groups and highlights according to a custom style definition", () => {
  const style = { max_words: 1, max_characters: 100, line_width: 30, highlight_words: false };
  const groups = captionGroups(words, style);
  expect(groups).toHaveLength(3);
  expect(captionAt(groups, 0.2, style)).toEqual({ text: "Hello", active_word: null });
});


it("rejects a word just beyond the source duration", () => {
  expect(validateCaptionWords([{ text: "End", start: 0, end: 1.005 }], 1)).toContain("check");
});
