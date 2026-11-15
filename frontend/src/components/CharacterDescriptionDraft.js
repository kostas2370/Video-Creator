import { useEffect, useRef, useState } from "react";
import { draftCharacterDescription } from "../api/apiService";
import { editorInput } from "./ui/EditorDialog";
import { useDraftSection } from "../hooks/useCreationDraft";

const profileFields = ["name", "appearance", "wardrobe", "personality", "relationships"];

function validDraft(value) {
  return value && !Array.isArray(value)
    && typeof value.name === "string" && value.name.trim()
    && typeof value.appearance === "string" && value.appearance.trim()
    && profileFields.every(key => value[key] == null || typeof value[key] === "string");
}

export function CharacterDescriptionDraft({
  character, premise, visualStyle, storyFormat, castNames, onUse,
  creating = false, disabled = false,
}) {
  const [saved, updateSaved] = useDraftSection(`description:${character.id}`, { idea: "", draft: null });
  const idea = typeof saved.idea === "string" ? saved.idea : "";
  const draft = validDraft(saved.draft) ? saved.draft : null;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const running = useRef(false);
  const mounted = useRef(true);
  const ready = !!premise?.trim() && !!visualStyle?.trim();

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const setDraft = value => updateSaved(previous => ({ ...previous, draft: value }));
  const generate = async () => {
    if (running.current || disabled || !ready) return;
    running.current = true;
    setBusy(true);
    setError("");
    try {
      const seed = Object.fromEntries(profileFields.map(key => [key, character[key] || ""]));
      const response = await draftCharacterDescription({
        ...seed, idea, premise, visual_style: visualStyle,
        story_format: storyFormat, cast_names: castNames,
      });
      if (!mounted.current) return;
      if (!response.ok) throw new Error(response.message || "Could not write this character. Please try again.");
      if (!validDraft(response.data?.character)) {
        throw new Error("AI returned an incomplete character description. Please try again.");
      }
      setDraft(Object.fromEntries(profileFields.map(key => [key, response.data.character[key] || ""])));
    } catch (reason) {
      if (mounted.current) setError(reason.message || "Could not write this character. Please try again.");
    } finally {
      running.current = false;
      if (mounted.current) setBusy(false);
    }
  };

  return (
    <div className="space-y-3 rounded-xl bg-indigo-50/70 p-4 dark:bg-indigo-900/30" aria-busy={busy}>
      <label className="block text-xs font-semibold">
        {creating ? "New character idea" : "Character idea"} <span className="font-normal text-gray-500">· optional</span>
        <input
          maxLength={500} value={idea} disabled={busy || disabled}
          onChange={event => updateSaved(previous => ({ ...previous, idea: event.target.value }))}
          placeholder="A shy banana detective with a secret…" className={`${editorInput} mt-2`}
        />
      </label>
      <button type="button" disabled={busy || disabled || !ready} onClick={generate} className="text-sm font-semibold text-indigo-600 disabled:opacity-50 dark:text-indigo-300">
        {busy ? "Writing description…" : creating ? "Create character with AI" : "Write description with AI"}
      </button>
      <p className="text-xs text-gray-500 dark:text-gray-400">
        {ready
          ? "Uses your AI text provider. Review the draft before using it."
          : "Add a series idea and visual style in Idea before generating a character."}
      </p>
      {error && <p role="alert" className="text-sm text-red-600 dark:text-red-300">{error}</p>}
      {draft && (
        <div className="space-y-3 border-t border-indigo-200 pt-3 dark:border-indigo-800">
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-300">
            {creating ? "Review new character" : "Description draft"}
          </p>
          <p className="text-sm font-semibold">{draft.name}</p>
          <dl className="space-y-2 text-sm">
            {[["Appearance", "appearance"], ["Wardrobe", "wardrobe"], ["Personality", "personality"], ["Relationships", "relationships"]]
              .filter(([, key]) => draft[key]).map(([label, key]) => (
                <div key={key}><dt className="text-xs text-gray-500">{label}</dt><dd>{draft[key]}</dd></div>
              ))}
          </dl>
          <div className="flex flex-wrap gap-4">
            <button type="button" disabled={disabled || busy} onClick={() => { onUse(draft); setDraft(null); }} className="text-sm font-semibold text-indigo-600 disabled:opacity-50 dark:text-indigo-300">
              {creating ? "Add this character" : "Use description"}
            </button>
            <button type="button" disabled={busy} onClick={() => setDraft(null)} className="text-sm text-gray-500">
              {creating ? "Discard draft" : "Keep current description"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
