import { videoFontFamily } from "./fonts";

const TEXT_WIDTH = 88;
export const overlayLineHeight = 1.5;

export function overlayTextMeasure(font) {
  if (typeof document === "undefined") return text => [...text].length * 0.6;
  const context = document.createElement("canvas").getContext("2d");
  context.font = `700 1000px ${videoFontFamily(font)}`;
  return text => {
    const metrics = context.measureText(text);
    return Math.max(metrics.width, (metrics.actualBoundingBoxLeft || 0) + (metrics.actualBoundingBoxRight || 0)) / 1000;
  };
}

export function wrapOverlayText(text, size, measure) {
  const paragraphs = [];
  for (const paragraph of text.split("\n")) {
    const lines = [];
    let current = "";
    for (const word of paragraph.match(/\S+/gu) || []) {
      const candidate = current ? `${current} ${word}` : word;
      if (measure(candidate) * size <= TEXT_WIDTH) { current = candidate; continue; }
      if (current) { lines.push(current); current = ""; }
      for (const character of word) {
        if (current && measure(current + character) * size > TEXT_WIDTH) { lines.push(current); current = ""; }
        current += character;
      }
    }
    lines.push(current);
    paragraphs.push(...lines);
  }
  return paragraphs.join("\n");
}

export function overlayTextLayout(text, size, frameSize, measure) {
  text = text.replace(/\\/g, "＼").replace(/{/g, "｛").replace(/}/g, "｝").replace(/\r/g, "");
  const maxHeight = 88 * frameSize[1] / frameSize[0];
  const layout = value => {
    const wrapped = wrapOverlayText(text, value, measure);
    return { text: wrapped, size: value, fits: wrapped.split("\n").length * value * overlayLineHeight <= maxHeight };
  };
  const original = layout(size);
  if (original.fits) return original;
  let low = 0, high = size;
  for (let index = 0; index < 20; index++) {
    const middle = (low + high) / 2;
    if (layout(middle).fits) low = middle; else high = middle;
  }
  return layout(low);
}
