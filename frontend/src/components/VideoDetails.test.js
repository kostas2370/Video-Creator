import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("../api/apiService", () => ({ draftVideoTags: vi.fn(), saveVideoDetails: vi.fn(), draftYouTubeDescription: vi.fn() }));
import { VideoDetails } from "./VideoDetails";

describe("compact video details action", () => {
  it("shows a single dialog launcher without filling the editor with tag fields", () => {
    const html = renderToStaticMarkup(<VideoDetails video={{ id: "video-1", title: "My video" }} open={false} onOpenChange={() => {}} onSaved={() => {}} />);
    expect(html.match(/Video details/g)).toHaveLength(1);
    expect(html).toContain('aria-haspopup="dialog"');
    expect(html).not.toContain("<textarea");
    expect(html).not.toContain("<section");
  });
  it("keeps saved tags out of the page until the dialog is opened", () => {
    const tags = { tiktok: ["OceanLife"], youtube: ["marine animals"], search: ["wildlife"] };
    const html = renderToStaticMarkup(<VideoDetails video={{ id: "video-1", title: "My video", tags }} open={false} onOpenChange={() => {}} onSaved={() => {}} />);
    expect(html).not.toContain("OceanLife");
    expect(html).not.toContain("marine animals");
    expect(html).not.toContain("wildlife");
  });
});
