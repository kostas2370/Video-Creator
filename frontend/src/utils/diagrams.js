// Keep geometry in step with utils/diagrams.py; shared fixtures cover every template.
import { wrapOverlayText } from "./overlayText";

export const diagramTemplates = {
  comparison: { label: "Comparison", inset: .12, markers: false, rail: false, maxItems: 2 },
  timeline: { label: "Timeline", inset: .22, markers: true, rail: true, maxItems: 4 },
  steps: { label: "Step by step", inset: .22, markers: true, rail: false, maxItems: 4 },
  flow: { label: "Animated flow", inset: .22, markers: true, rail: false, flow: true, maxItems: 4, description: "Connects stages with arrows and moving markers to show direction." },
};
const wideGlyphs = new Set([..."WMwm@%"]);
const colors = ["#38bdf8", "#fbbf24", "#a78bfa", "#34d399"];
export const newDiagram = template => ({ template, title: "", items: [{ label: "", detail: "" }, { label: "", detail: "" }] });

export function diagramPlan(diagram, [width, height], duration) {
  const config = diagramTemplates[diagram.template];
  const items = diagram.items;
  const rowHeight = height * .51 / items.length;
  const reveal = Math.min(.35, duration * .08);
  const elements = [];
  const rect = (x, y, w, h, color, start = 0, grow = false) => elements.push({ kind: "rect", x, y, width: w, height: h, color, start, grow, reveal });
  const text = (value, x, y, maxWidth, fontSize, maxHeight, color, start = 0) => {
    const columns = Math.max(1, Math.floor(maxWidth / (fontSize * .7)));
    const wrapped = wrapOverlayText(value.replace(/\s+/gu, " ").trim(), 1, text => [...text].length, columns);
    const lines = wrapped.split("\n");
    elements.push({ kind: "text", x, y, text: wrapped, size: Math.min(fontSize, maxHeight / (lines.length * 1.3), maxWidth / (Math.max(1, ...lines.map(value => [...value].reduce((sum, char) => sum + (wideGlyphs.has(char) || char.codePointAt(0) >= 0x2e80 ? 1.05 : .65), 0))))), color, start, reveal });
  };
  rect(0, 0, width, height, "#0f172a");
  text(diagram.title || "", width * .1, height * .11, width * .8, Math.min(width * .065, height * .065), height * .12, "#ffffff");
  if (config.rail) rect(width * .135, height * .29, width * .004, rowHeight * (items.length - 1), "#475569");
  items.forEach((item, index) => {
    const y = height * .27 + index * rowHeight;
    const start = config.flow ? 0 : duration * .65 * index / Math.max(1, items.length - 1);
    const color = colors[index];
    const x = width * config.inset;
    const cardWidth = width * (.9 - config.inset);
    rect(x - width * .025, y - rowHeight * .07, cardWidth + width * .025, rowHeight * .87, "#1e293b", start);
    rect(x, y, cardWidth * .92, Math.max(2, height * .004), color, start, true);
    const font = Math.min(width * .055, rowHeight * .23);
    text(item.label, x, y + rowHeight * .08, cardWidth * .92, font, rowHeight * .28, color, start);
    text(item.detail || "", x, y + rowHeight * .38, cardWidth * .92, font * .8, rowHeight * .35, "#ffffff", start);
    if (config.markers) {
      const edge = Math.min(width * .06, rowHeight * .28);
      rect(width * .137 - edge / 2, y, edge, edge, color, start);
      text(String(index + 1), width * .137 - edge * .22, y + edge * .08, edge * .6, edge * .6, edge, "#0f172a", start);
      if (config.flow && index < items.length - 1) {
        const top = y + edge + height * .008;
        const bottom = y + rowHeight - height * .012;
        const head = Math.min(width * .035, rowHeight * .1);
        const center = width * .137;
        rect(center - width * .003, top, width * .006, bottom - top - head, color);
        elements.push({ kind: "arrow", x: center - head / 2, y: bottom - head, width: head, height: head, color, start: 0, reveal });
        const period = Math.max(.001, Math.min(1.4, duration * .24));
        const dot = Math.min(width * .018, head * .65);
        rect(center - dot / 2, top, dot, dot, "#ffffff", index * period / 3);
        elements.at(-1).motion = { to_y: bottom - head - dot, period };
      }
    }
  });
  return elements;
}

export function diagramElementState(element, time) {
  const elapsed = time - element.start;
  const motion = element.motion;
  const y = motion ? element.y + (motion.to_y - element.y) * ((Math.max(0, elapsed) % motion.period) / motion.period) : element.y;
  return { x: element.x, y, visible: elapsed >= 0, progress: Math.min(1, Math.max(0, elapsed / element.reveal)) };
}
