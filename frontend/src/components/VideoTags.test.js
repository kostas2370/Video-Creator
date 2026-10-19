import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("../api/apiService", () => ({ generateVideoTags: vi.fn(), saveVideoTags: vi.fn() }));
import { VideoTags } from "./VideoTags";

describe("compact video tags action", () => {
  it("shows a single dialog launcher without filling the editor with tag fields", () => {
    const html = renderToStaticMarkup(<VideoTags videoId="video-1" onSaved={() => {}} />);
    expect(html.match(/aria-label="Video tags"/g)).toHaveLength(1);
    expect(html).toContain('aria-haspopup="dialog"');
    expect(html).not.toContain("<textarea");
    expect(html).not.toContain("<section");
  });
  it("keeps saved tags out of the page until the dialog is opened", () => {
    const tags = { tiktok: ["OceanLife"], youtube: ["marine animals"], search: ["wildlife"] };
    const html = renderToStaticMarkup(<VideoTags videoId="video-1" tags={tags} onSaved={() => {}} />);
    expect(html).not.toContain("OceanLife");
    expect(html).not.toContain("marine animals");
    expect(html).not.toContain("wildlife");
  });
});
