export function isVideo(source) {
  return source?.type?.startsWith("video/") || /\.(mp4|mov|webm|avi|m4v)(?:[?#]|$)/i.test(source?.name ?? source ?? "");
}
