export const defaultCaptionStyle = { preset: "TIKTOK", font: "DejaVu Sans", size: 6, color: "#ffffff", highlight: "#ffe846", position: "bottom" };
export const captionBusy = status => ["QUEUED", "TRANSCRIBING", "RENDER_QUEUED", "RENDERING"].includes(status);

// Video previews receive the resolved definition from the backend. These defaults
// also support existing callers that only supply a legacy preset name.
export function resolveCaptionConfig(preset = "CLASSIC", config) {
  if (config?.font_size != null) return config;
  if (preset && typeof preset === "object") return preset;
  const highlighted = preset === "TIKTOK";
  const base = {
    font: "DejaVu Sans", font_size: highlighted ? 6 : 48, scale_with_frame: highlighted,
    color: "#ffffff", highlight_color: "#ffe846", outline_color: "#000000",
    outline_width: highlighted ? 0.45 : 2, shadow: highlighted ? 0.2 : 0,
    bold: highlighted, uppercase: highlighted, highlight_words: highlighted,
    position: "bottom", margin_left: 8, margin_right: highlighted ? 14 : 8,
    margin_vertical: highlighted ? 9 : 5, portrait_margin_vertical: highlighted ? 22 : 5,
    line_width: highlighted ? 20 : 32, max_words: highlighted ? 4 : 10,
    max_characters: highlighted ? 38 : 62,
  };
  if (!config) return base;
  // Compatibility for the standalone caption studio's original appearance fields.
  return { ...base, font: config.font || base.font, font_size: config.size || 6,
    scale_with_frame: true, color: config.color || base.color,
    highlight_color: config.highlight || base.highlight_color,
    outline_width: 0.45, shadow: 0, position: config.position || "bottom",
    margin_right: 14, margin_vertical: 9, portrait_margin_vertical: 22 };
}

export function captionGroups(words, preset = "TIKTOK") {
  const groups = [];
  let current = [];
  const style = resolveCaptionConfig(preset);
  const limit = style.max_words;
  const characters = style.max_characters;
  for (const word of words) {
    const candidate = [...current, word].map(item => item.text).join(" ");
    if (current.length && (current.length >= limit || [...candidate].length > characters || word.start - current[current.length - 1].end > 0.5)) {
      groups.push(current); current = [];
    }
    current.push(word);
    if (/[.!?;…]["”’')]*$/u.test(word.text)) { groups.push(current); current = []; }
  }
  if (current.length) groups.push(current);
  return groups;
}

export function captionAt(groups, time, preset = "TIKTOK") {
  const group = groups.find(items => time >= items[0].start && time < items[items.length - 1].end);
  if (!group) return null;
  const style = resolveCaptionConfig(preset);
  const width = style.line_width;
  const lines = [];
  let line = "";
  for (const word of group) {
    if (line && [...`${line} ${word.text}`].length > width) { lines.push(line); line = ""; }
    line = line ? `${line} ${word.text}` : word.text;
  }
  if (line) lines.push(line);
  let active = 0;
  group.forEach((word, index) => { if (time >= word.start) active = index; });
  return { text: lines.join("\n"), active_word: style.highlight_words ? active : null };
}

export function validateCaptionWords(words, duration) {
  let previous = 0;
  for (const [index, word] of words.entries()) {
    if (!word.text.trim() || /\s/u.test(word.text.trim()) || [...word.text].length > 40) return `Word ${index + 1}: enter one word, up to 40 characters.`;
    if (!Number.isFinite(word.start) || !Number.isFinite(word.end) || word.start < previous || word.end <= word.start || word.end > duration + 1e-9) return `Word ${index + 1}: check its start and end times. Words must stay in order without overlapping.`;
    previous = word.end;
  }
  return "";
}

// Insert into a free interval at the playhead without shifting existing words.
export function insertCaptionWord(words, time, duration) {
  const next = words.findIndex(word => word.start > time);
  const index = next < 0 ? words.length : next;
  const start = Math.ceil(Math.max(time, index > 0 ? words[index - 1].end : 0) * 1000) / 1000;
  const end = Math.floor(Math.min(duration, words[index]?.start ?? duration, start + 0.3) * 1000) / 1000;
  if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end <= start) return null;
  return { index, words: [...words.slice(0, index), { text: "", start, end }, ...words.slice(index)] };
}
