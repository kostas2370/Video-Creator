export function creationDraftOwner(user, token) {
  if (user?.id) return String(user.id);
  try {
    const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return String(JSON.parse(atob(payload)).user_id || "");
  } catch { return ""; }
}

export const creationDraftKey = (owner, kind) => owner ? `viddie:creation:v1:${encodeURIComponent(owner)}:${kind}` : null;

export function readCreationDraft(key) {
  if (!key) return null;
  try {
    const record = JSON.parse(localStorage.getItem(key) || "null");
    return record?.version === 1 && record.value && typeof record.value === "object" && !Array.isArray(record.value) ? record : null;
  } catch { return null; }
}

export function mergeDraft(defaults, saved) {
  if (!saved || typeof saved !== "object" || Array.isArray(saved)) return defaults;
  return Object.fromEntries(Object.entries(defaults).map(([key, value]) => {
    const stored = saved[key];
    if (value === null) return [key, stored === null || typeof stored === "string" ? stored ?? value : value];
    if (Array.isArray(value)) return [key, Array.isArray(stored) ? stored : value];
    if (typeof value === "object") return [key, mergeDraft(value, stored)];
    return [key, typeof stored === typeof value ? stored : value];
  }));
}

export function restoreWizardDraft(saved, defaults) {
  const value = mergeDraft(defaults, saved);
  if (saved.form && ["number", "string"].includes(typeof saved.form.scene_count)) value.form.scene_count = saved.form.scene_count;
  if (Array.isArray(value.form?.cast)) value.form.cast = value.form.cast.filter(character => character && ["id", "name", "appearance"].every(key => typeof character[key] === "string"));
  value.step = [0, 1, 2].includes(value.step) ? value.step : 0;
  value.ui = saved.ui && typeof saved.ui === "object" && !Array.isArray(saved.ui) ? saved.ui : {};
  return value;
}
