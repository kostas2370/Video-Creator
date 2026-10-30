import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { FullVideoTranscript, transcriptParagraphs, transcriptText } from "./FullVideoTranscript";

it("shows the full source transcript including words beyond any short clip", () => {
  const words = [{ text: "Opening", start: 0, end: 1 }, { text: "Closing", start: 3600, end: 3601 }];
  const html = renderToStaticMarkup(<FullVideoTranscript title="Full interview" words={words} />);
  expect(html).toContain("Opening");
  expect(html).toContain("Closing");
  expect(html).toContain("60:00");
  expect(html).toContain("Copy full transcript");
  expect(html).toContain("Download TXT");
  expect(transcriptText(transcriptParagraphs(words))).toBe("[0:00] Opening\n\n[60:00] Closing");
});

it("keeps all words in long transcripts when grouping readable passages", () => {
  const words = Array.from({ length: 245 }, (_, i) => ({ text: `word${i}`, start: i, end: i + 0.8 }));
  const paragraphs = transcriptParagraphs(words);
  expect(paragraphs).toHaveLength(5);
  expect(paragraphs.map(p => p.text).join(" ")).toBe(words.map(word => word.text).join(" "));
});
