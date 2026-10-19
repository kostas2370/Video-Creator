import fontManifest from "../generated/videoFonts.json";

export const videoFonts = fontManifest.map(font => font.family);

export function videoFontFamily(font = "DejaVu Sans") {
  const selected = fontManifest.find(entry => entry.family === font) || fontManifest[0];
  return `"${selected.family}", ${selected.fallback}`;
}

// Preserve a preset's appearance when selecting a different font. Custom styles
// express sizes as a percentage of the shorter frame dimension, unlike Classic.
export function captionWithFont(style, font, size) {
  const { scale_with_frame, ...config } = style;
  const scale = scale_with_frame === false ? 100 / Math.min(...size) : 1;
  return { ...config, font,
    font_size: Math.max(1, Math.min(15, style.font_size * scale)),
    outline_width: Math.max(0, Math.min(1.5, style.outline_width * scale)),
    shadow: Math.max(0, Math.min(1, style.shadow * scale)) };
}
