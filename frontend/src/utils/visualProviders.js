// Keep picker labels and capabilities together so new providers need one UI entry.
const providers = {
  OPENAI: { label: "OpenAI images", reference: true },
  sora: { label: "OpenAI Sora (retired)", reference: true, video: true, retired: true },
  kling: { label: "Kling O3 · fal.ai (video)", reference: true, video: true },
  runway: { label: "Runway Gen-4.5 (video)", reference: true, video: true },
  "gemini-video": { label: "Gemini Omni Flash (video)", reference: true, video: true },
  midjourney: { label: "Midjourney" },
  "stable-diffusion": { label: "Stable Diffusion" },
};

export const visualProviderNames = Object.fromEntries(
  Object.entries(providers).filter(([, provider]) => !provider.retired).map(([name, provider]) => [name, provider.label])
);

export const isBuiltinVisualProvider = name =>
  Object.prototype.hasOwnProperty.call(providers, name);

export const supportsVisualReference = (name, mode) =>
  mode === "AI" && isBuiltinVisualProvider(name) && providers[name].reference === true;

export const isBuiltinVideoProvider = name =>
  isBuiltinVisualProvider(name) && providers[name].video === true;

const reservedNames = new Set(
  [...Object.keys(providers), "stable_diffusion", "bing", "google"].map(name => name.toLowerCase())
);

export const isReservedVisualProvider = name => reservedNames.has(name.trim().toLowerCase());
