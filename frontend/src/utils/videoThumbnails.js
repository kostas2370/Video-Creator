import { ensureVideoThumbnail } from "../api/apiService";

const requests = new Map();
export const thumbnailRequestKey = video => `${video.id}:${video.updated_at || ""}:${video.output || video.preview_media?.url || ""}`;

// Share work across grid/list switches and React's repeated development effects.
export function loadVideoThumbnail(video) {
  const key = thumbnailRequestKey(video);
  if (requests.has(key)) return requests.get(key);
  const pending = ensureVideoThumbnail(video.id).then(result => {
    if (!result.ok) requests.delete(key);
    return result;
  }, error => {
    requests.delete(key);
    throw error;
  });
  if (requests.size >= 100) requests.delete(requests.keys().next().value);
  requests.set(key, pending);
  return pending;
}
