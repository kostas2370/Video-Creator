import React from "react";
import { generateIdeas } from "../api/apiService";
import { useDraftSection } from "../hooks/useCreationDraft";
import { useAIRequest } from "../hooks/useAIRequest";
import { editorInput } from "./ui/EditorDialog";

export function IdeaGenerator({ kind, seed = "", preferences = {}, disabled = false, onUse }) {
  const [saved, updateSaved] = useDraftSection(`ideas:${kind}`, { seed: "", ideas: [] });
  const { busy, error, run } = useAIRequest();
  const ideas = Array.isArray(saved.ideas) ? saved.ideas : [];
  const generate = async () => {
    if (busy || disabled) return;
    await run(
      () => generateIdeas({ ...preferences, kind, seed: saved.seed.trim() || seed.trim() }),
      data => updateSaved(previous => ({ ...previous, ideas: data.ideas })),
      "Could not suggest ideas. Please try again.",
    );
  };
  return (
    <div className="mt-4 space-y-3">
      <label className="block text-sm">Topic or inspiration <span className="text-gray-400">· optional</span><input maxLength={2000} value={saved.seed} disabled={busy || disabled} onChange={event => updateSaved(previous => ({ ...previous, seed: event.target.value }))} placeholder={seed ? "Use your current idea, or try a different topic" : "Space, unlikely friendships, everyday mysteries…"} className={`${editorInput} mt-2`} /></label>
      <div className="flex flex-wrap items-center gap-3"><button type="button" disabled={busy || disabled} onClick={generate} className="rounded-lg border border-indigo-200 px-3 py-2 text-sm font-semibold text-indigo-600 disabled:opacity-50 dark:border-indigo-800 dark:text-indigo-300">{busy ? "Finding ideas…" : ideas.length ? "Suggest more ideas" : `Suggest ${kind} ideas`}</button><p className="text-xs text-gray-500">{seed ? "Uses your current idea unless you add a topic." : "Leave the topic blank for a surprise."} One paid AI request.</p></div>
      {busy && <p role="status" className="text-xs text-gray-500">Preparing three ideas for you to choose from…</p>}
      {error && <p role="alert" className="text-sm text-red-600 dark:text-red-300">{error}</p>}
      {ideas.length > 0 && <div className="space-y-3">
        <p className="text-xs text-gray-500">Choose an idea to replace {kind === "series" ? "the name and premise" : "your prompt"} in this form.</p>
        {ideas.map((idea, index) => <article key={index} className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"><h4 className="text-sm font-semibold">{idea.title}</h4><p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-gray-500 dark:text-gray-400">{idea.prompt}</p><button type="button" disabled={busy || disabled} onClick={() => onUse(idea)} aria-label={`Use idea: ${idea.title}`} className="mt-3 text-sm font-semibold text-indigo-600 disabled:opacity-50 dark:text-indigo-300">Use this idea</button></article>)}
      </div>}
    </div>
  );
}
