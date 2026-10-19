export function CaptionLayer({ cue, style = "CLASSIC", size = [1080, 1920], config }) {
  if (!cue) return null;
  const tiktok = style === "TIKTOK";
  const unit = Math.min(1, size[1] / size[0]);
  const position = config?.position || "bottom";
  const longestLine = Math.max(...cue.text.split("\n").map(line => [...line].length), 1);
  const fit = config ? Math.min(1, (tiktok ? 20 * 6 : 32 * 4) / config.size / longestLine) : 1;
  const fallbackFont = config?.font?.includes("Mono") ? "monospace" : config?.font?.includes("Serif") ? "Georgia, serif" : "Arial, sans-serif";
  let word = -1;
  return <div className="pointer-events-none absolute inset-0 z-10" style={{ containerType: "inline-size" }}>
    <div data-preview-caption style={{
      position: "absolute", left: "8%", right: tiktok || config ? "14%" : "8%",
      ...(position === "middle" ? { top: "50%", transform: "translateY(-50%)" } : position === "top" ? { top: "9%" } : { bottom: tiktok || config ? (size[1] > size[0] ? "22%" : "9%") : "5%" }),
      textAlign: "center", whiteSpace: "pre-line", lineHeight: 1.16,
      fontFamily: `"${config?.font || "DejaVu Sans"}", ${fallbackFont}`, fontWeight: tiktok ? 800 : 400,
      fontSize: `${(config ? config.size * unit : tiktok ? 6 * unit : 4800 / size[0]) * fit}cqw`, color: config?.color || "white",
      WebkitTextStroke: `${tiktok || config ? 0.45 * unit : 200 / size[0]}cqw black`,
      paintOrder: "stroke fill", textShadow: tiktok && !config ? "0 0.2em 0.1em #0008" : undefined,
    }}>
      {tiktok ? cue.text.split(/(\s+)/u).map((token, index) => {
        if (!token.trim()) return token;
        word += 1;
        return <span key={index} style={{ color: word === cue.active_word ? (config?.highlight || "#ffe846") : (config?.color || "white") }}>{token.toUpperCase()}</span>;
      }) : cue.text}
    </div>
  </div>;
}
