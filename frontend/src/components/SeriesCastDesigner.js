import { useState } from "react";
import { draftSeriesCast } from "../api/apiService";
import { editorInput } from "./ui/EditorDialog";
import { useDraftSection } from "../hooks/useCreationDraft";

export function SeriesCastDesigner({ premise, visualStyle, storyFormat, hasCast, onUse }) {
  const [saved, updateSaved] = useDraftSection("cast-proposal", { count: 2, draft: null });
  const count = saved.count || 2;
  const draft = Array.isArray(saved.draft) ? saved.draft : null;
  const setCount = value => updateSaved(previous => ({ ...previous, count: value }));
  const setDraft = value => updateSaved(previous => ({ ...previous, draft: value }));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const generate = async () => {
    if (busy) return;
    setBusy(true); setError("");
    const response = await draftSeriesCast({ premise, visual_style: visualStyle, story_format: storyFormat, count: Number(count) });
    if (response.ok) setDraft(response.data.cast); else setError(response.message);
    setBusy(false);
  };
  return <div className="space-y-3 rounded-xl border border-indigo-200 bg-indigo-50/50 p-4 dark:border-indigo-800 dark:bg-indigo-900/30">
    <p className="text-sm text-gray-500 dark:text-gray-400">AI drafts names, appearances and personalities from your story. Review the cast before using it.</p>
    <div className="flex flex-wrap items-end gap-3"><label className="text-sm font-semibold">Number of characters<select value={count} onChange={event => setCount(event.target.value)} className={`${editorInput} mt-2`}>{[1, 2, 3, 4, 5, 6].map(value => <option key={value} value={value}>{value}</option>)}</select></label><button type="button" disabled={busy || !premise.trim() || !visualStyle.trim()} onClick={generate} className="rounded-lg border border-indigo-300 px-4 py-2 text-sm font-semibold text-indigo-600 disabled:opacity-50 dark:text-indigo-300">{busy ? "Designing characters…" : "Create characters with AI"}</button></div>
    <p className="text-xs text-gray-500">Uses your AI text provider.</p>
    {error && <p role="alert" className="text-sm text-red-600 dark:text-red-300">{error}</p>}
    {draft && <div className="space-y-4 border-t border-indigo-200 pt-4 dark:border-indigo-800"><h4 className="text-sm font-semibold">Review proposed cast</h4>{draft.map(character => <div key={character.id} className="text-sm"><p className="font-semibold">{character.name}</p><p>{character.appearance}</p><p className="text-xs text-gray-500">{character.wardrobe} · {character.personality}</p><p className="text-xs text-gray-500">{character.relationships}</p></div>)}{hasCast && <p className="text-xs text-amber-700 dark:text-amber-300">Using this draft replaces the character cards in this form. Existing episodes keep their original cast.</p>}<div className="flex gap-4"><button type="button" onClick={() => { onUse(draft); setDraft(null); }} className="text-sm font-semibold text-indigo-600 dark:text-indigo-300">Use proposed cast</button><button type="button" onClick={() => setDraft(null)} className="text-sm text-gray-500">Keep current cast</button></div></div>}
  </div>;
}
