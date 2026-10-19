import { resolveCaptionConfig } from "../utils/captions";

export function CaptionLayer({ cue, style = "CLASSIC", size = [1080, 1920], config }) {
  if (!cue) return null;
  const spec = resolveCaptionConfig(style, config);
  const factor = spec.scale_with_frame ? Math.min(...size) / size[0] : 100 / size[0];
  const vertical = spec.position === "top" ? spec.margin_vertical : size[1] > size[0] ? spec.portrait_margin_vertical : spec.margin_vertical;
  const longestLine = Math.max(...cue.text.split("\n").map(line => [...line].length), 1);
  const fit = Math.min(1, (100 - spec.margin_left - spec.margin_right) / (longestLine * spec.font_size * factor * 0.6));
  const fallbackFont = spec.font.includes("Mono") ? "monospace" : spec.font.includes("Serif") ? "Georgia, serif" : "Arial, sans-serif";
  const display = token => spec.uppercase ? token.toUpperCase() : token;
  let word = -1;
  return <div className="pointer-events-none absolute inset-0 z-10" style={{ containerType: "inline-size" }}>
    <div data-preview-caption style={{
      position: "absolute", left: `${spec.margin_left}%`, right: `${spec.margin_right}%`,
      ...(spec.position === "middle" ? { top: "50%", transform: "translateY(-50%)" } : spec.position === "top" ? { top: `${vertical}%` } : { bottom: `${vertical}%` }),
      textAlign: "center", whiteSpace: "pre-line", lineHeight: 1.16,
      fontFamily: `"${spec.font}", ${fallbackFont}`, fontWeight: spec.bold ? 800 : 400,
      fontSize: `${spec.font_size * factor * fit}cqw`, color: spec.color,
      WebkitTextStroke: `${spec.outline_width * factor}cqw ${spec.outline_color}`,
      paintOrder: "stroke fill", textShadow: spec.shadow ? `0 ${spec.shadow * factor}cqw ${spec.outline_width * factor}cqw #0008` : undefined,
    }}>
      {spec.highlight_words ? cue.text.split(/(\s+)/u).map((token, index) => {
        if (!token.trim()) return token;
        word += 1;
        return <span key={index} style={{ color: word === cue.active_word ? spec.highlight_color : spec.color }}>{display(token)}</span>;
      }) : display(cue.text)}
    </div>
  </div>;
}
