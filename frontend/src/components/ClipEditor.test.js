import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it, vi } from "vitest";
vi.mock("../api/apiService", () => ({ saveClip: vi.fn() }));
import { ClipEditor } from "./ClipEditor";

it("provides portrait preview, transcript trimming and editable captions before export", () => {
  const words = [{ text: "Hello", start: 0, end: 0.5 }];
  const html = renderToStaticMarkup(<ClipEditor project={{ id: "p", duration: 60, words, preview: "/media/preview.mp4" }} clip={{ id: "c", title: "A clip", start: 0, end: 20, words, layout: "FIT", crop_position: 50, captions: true, style: {}, revision: "saved" }} onSaved={() => {}} onClose={() => {}} />);
  expect(html).toContain("Full picture with blurred background");
  expect(html).toContain("Choose boundaries from the transcript");
  expect(html).toContain("Edit caption words and timing");
  expect(html).toContain("Save clip");
  expect(html).toContain("Close without saving");
  expect(html).toContain("exports use the original footage");
});
