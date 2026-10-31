import { useState } from "react";
import { draftCharacterDescription } from "../api/apiService";
import { editorInput } from "./ui/EditorDialog";
import { useDraftSection } from "../hooks/useCreationDraft";

export function CharacterDescriptionDraft({ character, premise, visualStyle, storyFormat, castNames, onUse }) {
  const [saved, updateSaved] = useDraftSection(`description:${character.id}`, { idea: "", draft: null });
  const idea = typeof saved.idea === "string" ? saved.idea : "";
  const draft = saved.draft && typeof saved.draft === "object" && !Array.isArray(saved.draft) ? saved.draft : null;
  const setIdea = value => updateSaved(previous => ({ ...previous, idea: value }));
  const setDraft = value => updateSaved(previous => ({ ...previous, draft: value }));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const generate = async () => {
    if (busy) return;
    setBusy(true); setError("");
    const seed = Object.fromEntries(["name", "appearance", "wardrobe", "personality", "relationships"].map(key => [key, character[key] || ""]));
    const response = await draftCharacterDescription({ ...seed, idea, premise, visual_style: visualStyle, story_format: storyFormat, cast_names: castNames });
    if (response.ok) setDraft(response.data.character); else setError(response.message);
    setBusy(false);
  };
  return <div className="space-y-3 rounded-xl bg-indigo-50/70 p-4 dark:bg-indigo-900/30">
    <label className="block text-xs font-semibold">Character idea <span className="font-normal text-gray-500">· optional</span><input maxLength={500} value={idea} onChange={event => setIdea(event.target.value)} placeholder="A shy banana detective with a secret…" className={`${editorInput} mt-2`} /></label>
    <button type="button" disabled={busy || !premise?.trim() || !visualStyle?.trim()} onClick={generate} className="text-sm font-semibold text-indigo-600 disabled:opacity-50 dark:text-indigo-300">{busy ? "Writing description…" : "Write description with AI"}</button>
    {error && <p role="alert" className="text-sm text-red-600 dark:text-red-300">{error}</p>}
    {draft && <div className="space-y-3 border-t border-indigo-200 pt-3 dark:border-indigo-800"><p className="text-xs font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-300">Description draft</p><p className="text-sm font-semibold">{draft.name}</p><dl className="space-y-2 text-sm">{[["Appearance", "appearance"], ["Wardrobe", "wardrobe"], ["Personality", "personality"], ["Relationships", "relationships"]].filter(([, key]) => draft[key]).map(([label, key]) => <div key={key}><dt className="text-xs text-gray-500">{label}</dt><dd>{draft[key]}</dd></div>)}</dl><div className="flex flex-wrap gap-4"><button type="button" onClick={() => { onUse(draft); setDraft(null); }} className="text-sm font-semibold text-indigo-600 dark:text-indigo-300">Use description</button><button type="button" onClick={() => setDraft(null)} className="text-sm text-gray-500">Keep current description</button></div></div>}
  </div>;
}
