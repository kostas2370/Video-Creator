export const defaultCaptionStyle = { preset: "TIKTOK", font: "DejaVu Sans", size: 6, color: "#ffffff", highlight: "#ffe846", position: "bottom" };
export const captionBusy = status => ["QUEUED", "TRANSCRIBING", "RENDER_QUEUED", "RENDERING"].includes(status);

export function captionGroups(words, preset = "TIKTOK") {
  const groups = [];
  let current = [];
  const limit = preset === "TIKTOK" ? 4 : 10;
  const characters = preset === "TIKTOK" ? 38 : 62;
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
  const width = preset === "TIKTOK" ? 20 : 32;
  const lines = [];
  let line = "";
  for (const word of group) {
    if (line && [...`${line} ${word.text}`].length > width) { lines.push(line); line = ""; }
    line = line ? `${line} ${word.text}` : word.text;
  }
  if (line) lines.push(line);
  let active = 0;
  group.forEach((word, index) => { if (time >= word.start) active = index; });
  return { text: lines.join("\n"), active_word: preset === "TIKTOK" ? active : null };
}

export function validateCaptionWords(words, duration) {
  let previous = 0;
  for (const [index, word] of words.entries()) {
    if (!word.text.trim() || /\s/u.test(word.text.trim()) || [...word.text].length > 40) return `Word ${index + 1}: enter one word, up to 40 characters.`;
    if (!Number.isFinite(word.start) || !Number.isFinite(word.end) || word.start < previous || word.end <= word.start || word.end > duration + 0.01) return `Word ${index + 1}: check its start and end times. Words must stay in order without overlapping.`;
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
