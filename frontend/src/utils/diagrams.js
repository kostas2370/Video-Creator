// Keep geometry in step with utils/diagrams.py; shared fixtures cover every template.
import { wrapOverlayText } from "./overlayText";

export const diagramTemplates = {
  comparison: { label: "Comparison", inset: .12, markers: false, rail: false, maxItems: 2 },
  timeline: { label: "Timeline", inset: .22, markers: true, rail: true, maxItems: 4 },
  steps: { label: "Step by step", inset: .22, markers: true, rail: false, maxItems: 4 },
  flow: { label: "Animated flow", inset: .22, markers: true, rail: false, flow: true, maxItems: 4, description: "Connects stages with arrows and moving markers to show direction." },
  graph: { label: "Icon graph", graph: true, maxItems: 6, description: "Connect icons horizontally, split into branches, or merge paths. Edit the arrows below." },
};
const wideGlyphs = new Set([..."WMwm@%"]);
const colors = ["#38bdf8", "#fbbf24", "#a78bfa", "#34d399", "#fb7185", "#fb923c"];
export const newDiagram = template => ({ template, title: "", items: [{ label: "", detail: "" }, { label: "", detail: "" }] });

export const graphConnections = diagram => diagram.connections ?? diagram.items.slice(1).map((_, i) => ({ source: i, target: i + 1, label: "" }));

export function graphLevels(count, connections) {
  const levels = Array(count).fill(0), incoming = Array(count).fill(0), outgoing = Array.from({ length: count }, () => []);
  for (const edge of connections) {
    if (edge.source === edge.target || edge.source < 0 || edge.target < 0 || edge.source >= count || edge.target >= count) throw new Error("Connections must join two different existing items.");
    incoming[edge.target]++;
    outgoing[edge.source].push(edge.target);
  }
  const queue = incoming.flatMap((degree, i) => degree === 0 ? [i] : []);
  let processed = 0;
  while (queue.length) {
    const source = queue.shift();
    processed++;
    for (const target of outgoing[source]) {
      levels[target] = Math.max(levels[target], levels[source] + 1);
      if (--incoming[target] === 0) queue.push(target);
    }
  }
  if (processed !== count) throw new Error("Connections must not form a loop. Use branches or merges instead.");
  return levels;
}

function graphPlan(diagram, [width, height], duration, elements, rect, text) {
  const connections = graphConnections(diagram);
  const levels = graphLevels(diagram.items.length, connections);
  const columns = Math.max(...levels) + 1;
  const nodeWidth = Math.min(width * .24, width * .76 / columns);
  const positions = [];
  for (let column = 0; column < columns; column++) {
    const group = levels.flatMap((level, index) => level === column ? [index] : []);
    group.forEach((index, row) => {
      const x = columns > 1 ? width * (.16 + .68 * column / Math.max(1, columns - 1)) : width * .5;
      const cellHeight = height * .43 / group.length;
      const y = height * .31 + cellHeight * (row + .25);
      const edge = Math.min(nodeWidth * .6, height * .12, cellHeight * .32);
      positions[index] = [x, y, edge, cellHeight];
    });
  }
  const reveal = Math.min(.35, duration * .08);
  const period = Math.max(.001, Math.min(1.8, duration * .4));
  const polygon = (points, color) => {
    const left = Math.min(...points.map(p => p[0])), top = Math.min(...points.map(p => p[1]));
    elements.push({ kind: "polygon", x: left, y: top, width: Math.max(...points.map(p => p[0])) - left, height: Math.max(...points.map(p => p[1])) - top, points: points.map(([x, y]) => [x-left, y-top]), color, start: 0, reveal });
  };
  connections.forEach((connection, index) => {
    const { source, target } = connection;
    const [sx, sy, se] = positions[source], [tx, ty, te] = positions[target];
    const x1 = sx + se / 2 + width * .012, x2 = tx - te / 2 - width * .02;
    const head = Math.min(width * .022, Math.max(1, x2-x1) * .2);
    const color = colors[source], mid = (x1 + x2) / 2;
    let points = [[x1, sy], [mid, sy], [mid, ty], [x2-head, ty]];
    if (levels[target] - levels[source] > 1) {
      const lane = height * (.26 - index * .002);
      points = [[x1, sy], [x1 + width*.012, sy], [x1 + width*.012, lane], [x2-head-width*.012, lane], [x2-head-width*.012, ty], [x2-head, ty]];
    }
    const thickness = Math.max(2, width * .004);
    for (let i = 0; i < points.length - 1; i++) {
      const a = points[i], b = points[i + 1];
      const distance = Math.hypot(b[0]-a[0], b[1]-a[1]);
      if (!distance) continue;
      const dx = -(b[1]-a[1]) / distance * thickness / 2, dy = (b[0]-a[0]) / distance * thickness / 2;
      polygon([[a[0]+dx,a[1]+dy],[b[0]+dx,b[1]+dy],[b[0]-dx,b[1]-dy],[a[0]-dx,a[1]-dy]], color);
    }
    polygon([[x2-head,ty-head/2],[x2,ty],[x2-head,ty+head/2]], color);
    const dot = Math.min(width*.012, head*.65);
    const path = points.map(([x,y]) => [x-dot/2,y-dot/2]);
    rect(...path[0], dot, dot, "#ffffff");
    elements.at(-1).motion = { path, period };
    if (connection.label) text(connection.label, x1, Math.min(sy,ty)-height*.05, Math.max(width*.06,x2-x1), width*.026, height*.04, "#cbd5e1");
  });
  diagram.items.forEach((item, index) => {
    const [x,y,edge,cellHeight] = positions[index];
    if (item.icon) elements.push({ kind: "icon", icon: item.icon, x:x-edge/2, y:y-edge/2, width:edge, height:edge, start:0, reveal });
    else rect(x-edge/2,y-edge/2,edge,edge,colors[index]);
    text(item.label,x-nodeWidth/2,y+edge/2+cellHeight*.05,nodeWidth,Math.min(width*.042,nodeWidth*.22,cellHeight*.17),cellHeight*.25,colors[index]);
    elements.at(-1).centered = nodeWidth;
    if (item.detail) {
      text(item.detail,x-nodeWidth/2,y+edge/2+cellHeight*.33,nodeWidth,Math.min(width*.029,nodeWidth*.17,cellHeight*.13),cellHeight*.25,"#ffffff");
      elements.at(-1).centered = nodeWidth;
    }
  });
  return elements;
}

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
  if (config.graph) return graphPlan(diagram, [width, height], duration, elements, rect, text);
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
    const icon = item.icon;
    const iconEdge = icon ? Math.min(width * .075, rowHeight * .25) : 0;
    const labelWidth = cardWidth * .92 - (icon ? iconEdge + width * .02 : 0);
    if (icon) elements.push({ kind: "icon", icon, x: x + cardWidth * .92 - iconEdge, y: y + rowHeight * .08, width: iconEdge, height: iconEdge, start, reveal });
    text(item.label, x, y + rowHeight * .08, labelWidth, font, rowHeight * .28, color, start);
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
  let x = element.x, y = element.y;
  if (motion) {
    const points = motion.path || [[x,y],[motion.to_x ?? x,motion.to_y]];
    const lengths = points.slice(1).map((b,i) => Math.hypot(b[0]-points[i][0],b[1]-points[i][1]));
    const total = lengths.reduce((sum,value) => sum+value,0) || 1;
    let distance = (Math.max(0,elapsed) % motion.period) / motion.period * total;
    for (let i=0; i<lengths.length; i++) {
      if (!lengths[i]) continue;
      if (distance <= lengths[i]) {
        const fraction = distance/lengths[i], a=points[i], b=points[i+1];
        x = a[0]+(b[0]-a[0])*fraction; y = a[1]+(b[1]-a[1])*fraction;
        break;
      }
      distance -= lengths[i];
    }
  }
  return { x, y, visible: elapsed >= 0, progress: Math.min(1, Math.max(0, elapsed / element.reveal)) };
}
