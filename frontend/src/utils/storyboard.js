export function editableStoryboard(script) {
  const draft = JSON.parse(JSON.stringify(script));
  draft.scenes = (Array.isArray(draft.scenes) ? draft.scenes : []).flatMap(scene => {
    if (!Array.isArray(scene.sentences)) return [scene];
    return scene.sentences.map(({ sentence, ...visual }) => ({
      scene: scene.scene,
      ...visual,
      ...(sentence !== undefined ? { narration: sentence } : {}),
    }));
  });
  return draft;
}
