import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it, vi } from "vitest";
vi.mock("../api/apiService", () => ({ draftClipHashtags: vi.fn(), saveClipHashtags: vi.fn() }));
import { ClipHashtags } from "./ClipHashtags";

it("shows saved hashtags with generation, saving and copying controls", () => {
  const html = renderToStaticMarkup(<ClipHashtags projectId="p" clip={{ id: "c", title: "An interview", hashtags: ["Interview", "UsefulAdvice"] }} onSaved={() => {}} />);
  expect(html).toContain("#Interview #UsefulAdvice");
  expect(html).toContain("Generate hashtags");
  expect(html).toContain("Save hashtags");
  expect(html).toContain("Copy hashtags");
});
