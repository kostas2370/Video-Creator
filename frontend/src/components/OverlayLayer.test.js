import { describe, expect, it } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { OverlayLayer, wrapOverlayText } from "./OverlayLayer";

const overlay = { kind: "title", text: "Hello", logo: false, position: "bottom-left", start: 1, end: 3, size: 4, width: 20, color: "#ffffff", background: true, opacity: 1 };
const render = (item, time, duration = 5) => renderToStaticMarkup(<OverlayLayer overlays={[item]} time={time} duration={duration} />);

describe("overlay playback", () => {
  it("appears at the start and disappears exactly at the end", () => {
    expect(render(overlay, 0.99)).not.toContain("Hello");
    expect(render(overlay, 1)).toContain("Hello");
    expect(render(overlay, 3)).not.toContain("Hello");
  });
  it("clips open-ended overlays at scene boundaries", () => {
    expect(render({ ...overlay, end: null }, 4.9)).toContain("Hello");
    expect(render({ ...overlay, end: null }, 5)).not.toContain("Hello");
    expect(render(overlay, 2, 2)).not.toContain("Hello");
  });
  it("anchors corners and escapes markup", () => {
    const html = render({ ...overlay, text: "<script>bad</script>" }, 1);
    expect(html).toContain("left:5%");
    expect(html).toContain("top:95%");
    expect(html).toContain("translate(0%, -100%)");
    expect(html).toContain("&lt;script&gt;");
  });
  it("uses the selected font in the preview", () => {
    expect(render({ ...overlay, font: "Poppins" }, 1)).toContain("Poppins");
    expect(render(overlay, 1)).toContain("DejaVu Sans");
  });
  it("wraps long text and preserves deliberate line breaks", () => {
    expect(wrapOverlayText("One two three four five six seven eight nine ten\nNext line", 8)).toBe("One two three\nfour five six\nseven eight nine\nten\nNext line");
  });
});
