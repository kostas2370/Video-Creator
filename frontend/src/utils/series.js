export const defaultSeries = {
  title: "", premise: "", characters: "", visual_style: "", provider: "OPENAI",
  narration: true, voice_model: "", intro: "", outro: "", subtitles: true,
  video_format: "PORTRAIT", platform: "GENERAL", scene_count: 6,
};

export function seriesPayload(profile, file, removeReference = false) {
  const values = Object.fromEntries(Object.keys(defaultSeries).map(key => [key,
    ["voice_model", "intro", "outro"].includes(key) ? profile[key] || null : profile[key],
  ]));
  values.scene_count = Number(values.scene_count);
  values.remove_reference = removeReference;
  if (!file) return values;
  const data = new FormData();
  Object.entries(values).forEach(([key, value]) => data.append(key, value == null ? "" : String(value)));
  data.append("reference_image", file);
  return data;
}


export function episodeMemoryReducer(state, action) {
  switch (action.type) {
    case "generated": return { ...state, draft: action.value, sourceHash: action.sourceHash };
    case "edit": return { ...state, draft: action.value };
    case "remote":
      if (state.draft !== state.baseline) return state;
      return { ...state, draft: action.value, baseline: action.value, ...(action.sourceHash !== undefined ? { sourceHash: action.sourceHash } : {}) };
    case "saved":
    case "load": return { ...state, draft: action.value, baseline: action.value, ...(action.sourceHash !== undefined ? { sourceHash: action.sourceHash } : {}) };
    default: return state;
  }
}
