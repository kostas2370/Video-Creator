import { API_HOST } from "../endpoints";

export const mediaUrl = url => url && (/^https?:\/\//i.test(url) ? url : `${API_HOST}${url}`);

export function isVideo(source) {
  return source?.type?.startsWith("video/") || /\.(mp4|mov|webm|avi|m4v)(?:[?#]|$)/i.test(source?.name ?? source ?? "");
}
