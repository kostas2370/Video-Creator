import { describe, expect, it } from "vitest";
import { captionWithFont } from "./fonts";
import { resolveCaptionConfig } from "./captions";

describe("caption font changes", () => {
  it("preserves Classic size and outline when converting to a custom font", () => {
    const style = captionWithFont(resolveCaptionConfig("CLASSIC"), "Poppins", [1920, 1080]);
    expect(style.font).toBe("Poppins");
    expect(style.font_size * 1080 / 100).toBeCloseTo(48);
    expect(style.outline_width * 1080 / 100).toBeCloseTo(2);
    expect(style.highlight_words).toBe(false);
    expect(style.uppercase).toBe(false);
    expect(style).not.toHaveProperty("scale_with_frame");
  });
  it("retains highlighted caption sizing, colors and grouping", () => {
    const original = resolveCaptionConfig("TIKTOK");
    const style = captionWithFont(original, "Bebas Neue", [1080, 1920]);
    expect(style.font_size).toBe(original.font_size);
    expect(style.highlight_color).toBe(original.highlight_color);
    expect(style.max_words).toBe(original.max_words);
    expect(style.highlight_words).toBe(true);
  });
});
