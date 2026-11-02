import { useEffect, useMemo, useState } from "react";
import { overlayLineHeight, overlayTextLayout, overlayTextMeasure } from "../utils/overlayText";
import { videoFontFamily } from "../utils/fonts";
import { API_HOST } from "../endpoints";
import { overlayEntrance } from "../utils/photoAnimation";

export const overlayPositions = ["top-left", "top-center", "top-right", "middle-left", "middle-center", "middle-right", "bottom-left", "bottom-center", "bottom-right"];
const mediaUrl = url => /^https?:\/\//i.test(url) || url?.startsWith("blob:") ? url : `${API_HOST}${url}`;

function OverlayText({ item, style, frameSize }) {
  const [fontVersion, setFontVersion] = useState(0);
  useEffect(() => {
    let active = true;
    document.fonts?.load(`700 100px "${item.font || "DejaVu Sans"}"`).then(() => {
      if (active) setFontVersion(version => version + 1);
    }).catch(() => {});
    return () => { active = false; };
  }, [item.font]);
  const layout = useMemo(() => overlayTextLayout(
    item.text, item.size, frameSize, overlayTextMeasure(item.font),
  ), [item.text, item.size, item.font, frameSize[0], frameSize[1], fontVersion]);
  const [, horizontal] = item.position.split("-");
  return <div style={{
    ...style, color: item.color, fontSize: `${layout.size}cqw`,
    fontFamily: videoFontFamily(item.font), fontWeight: 700, lineHeight: overlayLineHeight,
    whiteSpace: "pre", textAlign: horizontal === "center" ? "center" : horizontal,
    background: item.background ? "black" : "transparent", padding: item.background ? "0.3cqw" : 0,
    textShadow: item.background ? undefined : "0 1px 1px black",
  }}>{layout.text}</div>;
}

export function OverlayLayer({ overlays = [], logo, time = 0, duration = Infinity, frameSize = [1920, 1080], animationPreset = "NONE" }) {
  return <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden" style={{ containerType: "inline-size" }}>
    {[...overlays.filter(item => item.logo), ...overlays.filter(item => !item.logo)].map((item, index) => {
      if (time < item.start || time >= Math.min(duration, item.end ?? duration)) return null;
      const [vertical, horizontal] = item.position.split("-");
      const column = { left: 0, center: 1, right: 2 }[horizontal];
      const row = { top: 0, middle: 1, bottom: 2 }[vertical];
      const entrance = overlayEntrance(item.logo || item.kind === "watermark" ? "NONE" : animationPreset, time - item.start, Math.min(duration, item.end ?? duration) - item.start);
      const style = { position: "absolute", left: `${[5, 50, 95][column]}%`, top: `${[5, 50, 95][row] + entrance.dy * 100}%`, transform: `translate(${-column * 50}%, ${-row * 50}%) scale(${entrance.scale})`, transformOrigin: `${column * 50}% ${row * 50}%`, opacity: item.opacity * entrance.opacity };
      return item.logo ? (logo && <img key={index} alt="" src={mediaUrl(logo)} style={{ ...style, width: `${item.width}%`, maxHeight: "50%", objectFit: "contain", objectPosition: `${horizontal} ${vertical === "middle" ? "center" : vertical}` }} />) : <OverlayText key={index} item={item} style={style} frameSize={frameSize} />;
    })}
  </div>;
}
