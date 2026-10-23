import { parseTagDraft } from "./videoTags";

export const youtubeTags = draft => parseTagDraft({ youtube: draft }).youtube;
export const youtubeTagLength = tags => tags.reduce((total, tag) => total + Array.from(tag).length + (tag.includes(" ") ? 2 : 0), Math.max(0, tags.length - 1));
export const descriptionBytes = text => new TextEncoder().encode(text).length;
export function appendTimestamps(description, timestamps) {
  const withoutChapters = description.replace(/(?:^|\n\n)Chapters\n(?:\d+:\d{2}(?::\d{2})? [^\n]+\n?)+/g, "").trim();
  return [withoutChapters, timestamps.trim()].filter(Boolean).join("\n\n");
}
