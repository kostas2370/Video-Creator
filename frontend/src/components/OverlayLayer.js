import { videoFontFamily } from "../utils/fonts";
import { API_HOST } from "../endpoints";

export const overlayPositions = ["top-left", "top-center", "top-right", "middle-left", "middle-center", "middle-right", "bottom-left", "bottom-center", "bottom-right"];
const mediaUrl = url => /^https?:\/\//i.test(url) || url?.startsWith("blob:") ? url : `${API_HOST}${url}`;

export function wrapOverlayText(text, size) {
  const columns = Math.max(10, Math.floor(140 / size));
  return text.split("\n").map(line => {
    const lines = [];
    let current = "";
    for (const word of line.trim().split(/\s+/).filter(Boolean)) {
      if (current && current.length + word.length + 1 > columns) { lines.push(current); current = ""; }
      let rest = word;
      if (current) current += " ";
      while (rest.length > columns) { lines.push(rest.slice(0, columns)); rest = rest.slice(columns); }
      current += rest;
    }
    if (current) lines.push(current);
    return lines.join("\n");
  }).join("\n");
}

export function OverlayLayer({ overlays = [], logo, time = 0, duration = Infinity }) {
  return <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden" style={{ containerType: "inline-size" }}>
    {[...overlays.filter(item => item.logo), ...overlays.filter(item => !item.logo)].map((item, index) => {
      if (time < item.start || time >= Math.min(duration, item.end ?? duration)) return null;
      const [vertical, horizontal] = item.position.split("-");
      const column = { left: 0, center: 1, right: 2 }[horizontal];
      const row = { top: 0, middle: 1, bottom: 2 }[vertical];
      const style = { position: "absolute", left: `${[5, 50, 95][column]}%`, top: `${[5, 50, 95][row]}%`, transform: `translate(${-column * 50}%, ${-row * 50}%)`, opacity: item.opacity };
      return item.logo ? (logo && <img key={index} alt="" src={mediaUrl(logo)} style={{ ...style, width: `${item.width}%`, maxHeight: "50%", objectFit: "contain", objectPosition: `${horizontal} ${vertical === "middle" ? "center" : vertical}` }} />) : <div key={index} style={{ ...style, color: item.color, fontSize: `${item.size}cqw`, fontFamily: videoFontFamily(item.font), fontWeight: 700, lineHeight: 1.2, whiteSpace: "pre", textAlign: horizontal === "center" ? "center" : horizontal, background: item.background ? "black" : "transparent", padding: item.background ? "0.3cqw" : 0, textShadow: item.background ? undefined : "0 1px 1px black" }}>{wrapOverlayText(item.text, item.size)}</div>;
    })}
  </div>;
}
