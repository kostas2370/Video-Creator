const keyFor = videoId => `editor-workspace:${videoId}`;

export function readWorkspace(videoId) {
  try {
    const value = JSON.parse(localStorage.getItem(keyFor(videoId)) || "null");
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch { return {}; }
}

export function saveWorkspace(videoId, changes) {
  try { localStorage.setItem(keyFor(videoId), JSON.stringify({ ...readWorkspace(videoId), ...changes })); }
  catch { /* Editing still works when browser storage is unavailable. */ }
}

export function rememberedScene(scenes, selectedId) {
  return scenes.find(scene => scene.id === selectedId) || scenes[0];
}

export const sameSceneOrder = (scenes, ids) => scenes.length === ids.length && scenes.every((scene, index) => scene.id === ids[index]);
