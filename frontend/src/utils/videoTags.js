export const tagGroups = [
  { key: "tiktok", shortLabel: "TikTok", label: "TikTok hashtags", hint: "Separate hashtags with spaces or commas." },
  { key: "youtube", shortLabel: "YouTube", label: "YouTube keywords", hint: "Separate keyword phrases with commas." },
  { key: "search", shortLabel: "Library", label: "Platform search tags", hint: "Separate topics with commas to help find this video in your library." },
];

export const tagDraft = (tags = {}) => Object.fromEntries(tagGroups.map(({ key }) => [key, (tags[key] || []).join(", ")]));

export function parseTagDraft(draft) {
  return Object.fromEntries(tagGroups.map(({ key }) => {
    const values = (draft[key] || "").split(key === "tiktok" ? /[,\s#]+/u : /[,\n]+/u);
    const unique = new Map();
    for (const value of values) {
      const tag = value.normalize("NFC").trim().replace(/^#+/, "").replace(/\s+/gu, " ");
      if (tag && !unique.has(tag.toLowerCase())) unique.set(tag.toLowerCase(), tag);
    }
    return [key, [...unique.values()]];
  }));
}

export const copyTagText = (key, tags) => key === "tiktok" ? tags.map(tag => `#${tag}`).join(" ") : tags.join(", ");
