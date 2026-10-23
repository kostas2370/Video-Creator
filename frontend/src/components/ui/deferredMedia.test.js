import React, { lazy } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { DeferredDialog } from "./DeferredDialog";
import { DeferredVideo } from "./DeferredVideo";

describe("deferred media and tools", () => {
  it("does not request an offscreen video's source while preserving playback attributes", () => {
    const html = renderToStaticMarkup(<DeferredVideo src="/media/large.mp4" controls muted playsInline aria-label="Scene clip" className="aspect-video" />);
    expect(html).not.toContain("/media/large.mp4");
    expect(html).toContain('preload="metadata"');
    expect(html).toContain('controls=""');
    expect(html).toContain('playsinline=""');
    expect(html).toContain('aria-label="Scene clip"');
  });

  it("preserves click-to-load behavior for library clips", () => {
    expect(renderToStaticMarkup(<DeferredVideo src="/media/clip.mp4" controls preload="none" />)).toContain('preload="none"');
  });

  it("does not start downloading an unopened dialog", () => {
    const download = vi.fn(() => Promise.resolve({ default: () => <p>Editor</p> }));
    const Editor = lazy(download);
    expect(renderToStaticMarkup(<DeferredDialog open={false} onClose={() => {}}><Editor /></DeferredDialog>)).toBe("");
    expect(download).not.toHaveBeenCalled();
  });
});
