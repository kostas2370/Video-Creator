export const defaultSeries = {
  title: "", premise: "", characters: "", visual_style: "", provider: "OPENAI",
  narration: true, voice_model: "", intro: "", outro: "", subtitles: true,
  video_format: "PORTRAIT", platform: "GENERAL", scene_count: 6,
  cast: [], story_format: "GENERAL",
};

export const storyFormats = [
  { value: "GENERAL", label: "General series", description: "Follow your premise and episode idea." },
  { value: "ANIMATED_STORY", label: "Animated character story", description: "Visual hook, conflict, escalation and an expressive payoff or cliffhanger." },
  { value: "SERIAL_DRAMA", label: "Serial drama", description: "Emotional hook, relationship stakes, a revelation and a cliffhanger for the next episode." },
];

export function characterApproval(character, visualStyle) {
  return Object.fromEntries(["reference_id", "name", "appearance", "wardrobe"].map(key => [key, character[key] || ""]).concat([["visual_style", visualStyle]]));
}

export function characterIsApproved(character, visualStyle) {
  const expected = characterApproval(character, visualStyle);
  return !!character.reference_id && Object.keys(expected).every(key => character.reference_approval?.[key] === expected[key]);
}

export function seriesPayload(profile, file, removeReference = false) {
  const values = Object.fromEntries(Object.keys(defaultSeries).map(key => [key,
    ["voice_model", "intro", "outro"].includes(key) ? profile[key] || null : profile[key],
  ]));
  values.scene_count = Number(values.scene_count);
  values.remove_reference = removeReference;
  if (!file) return values;
  const data = new FormData();
  Object.entries(values).forEach(([key, value]) => data.append(key, key === "cast" ? JSON.stringify(value) : value == null ? "" : String(value)));
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
