import { describe, expect, it } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { CaptionLayer } from "./CaptionLayer";

describe("TikTok captions", () => {
  it("highlights only the active word and preserves line breaks", () => {
    const html = renderToStaticMarkup(<CaptionLayer style="TIKTOK" cue={{ text: "Hear this\namazing story", active_word: 2 }} />);
    expect(html).toContain('color:#ffe846">AMAZING</span>');
    expect(html.match(/#ffe846/g)).toHaveLength(1);
    expect(html).toContain("\n");
    expect(html).toContain("bottom:22%");
    expect(html).toContain("font-size:6cqw");
  });
  it("scales to landscape and keeps classic text unchanged", () => {
    const cue = { text: "Hello <world>", active_word: null };
    const html = renderToStaticMarkup(<CaptionLayer style="CLASSIC" cue={cue} size={[1920, 1080]} />);
    expect(html).toContain("Hello &lt;world&gt;");
    expect(html).toContain("bottom:5%");
    expect(html).not.toContain("#ffe846");
    const landscape = renderToStaticMarkup(<CaptionLayer style="TIKTOK" cue={cue} size={[1920, 1080]} />);
    expect(landscape).toContain("bottom:9%");
    expect(landscape).toContain("font-size:3.375cqw");
  });
  it("renders no caption outside cue timing", () => {
    expect(renderToStaticMarkup(<CaptionLayer />)).toBe("");
  });
  it("applies custom colors, font, placement, and fits long words", () => {
    const html = renderToStaticMarkup(<CaptionLayer style="TIKTOK" cue={{ text: "a".repeat(30), active_word: 0 }} config={{ font: "DejaVu Serif", size: 6, color: "#aaffff", highlight: "#00ff00", position: "top" }} />);
    expect(html).toContain("top:9%");
    expect(html).toContain("font-size:4cqw");
    expect(html).toContain("Georgia, serif");
    expect(html).toContain("color:#00ff00");
  });
});
