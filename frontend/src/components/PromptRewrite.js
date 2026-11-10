import React from "react";
import { rewritePrompt } from "../api/apiService";
import { useDraftSection } from "../hooks/useCreationDraft";
import { useAIRequest } from "../hooks/useAIRequest";
import { editorInput } from "./ui/EditorDialog";

export function PromptRewrite({ kind, value, onUse, preferences = {}, disabled = false, scope = kind, embedded = false }) {
  const [saved, updateSaved] = useDraftSection(`rewrite:${scope}`, { instructions: "", draft: null, source: "", open: false });
  const { busy, error, run } = useAIRequest();
  const stale = !!saved.draft && saved.source !== value;
  const generate = async () => {
    if (busy || disabled || !value.trim() || value.length > 2000) return;
    const source = value;
    await run(
      () => rewritePrompt({ ...preferences, kind, prompt: source, instructions: saved.instructions }),
      data => updateSaved(previous => ({ ...previous, source, draft: data.prompt })),
      "Could not rewrite this prompt. Please try again.",
    );
  };
  const content = (
    <div className="mt-3 space-y-3">
      <label className="block text-xs">What would you like to change? <span className="text-gray-400">· optional</span><input maxLength={500} value={saved.instructions} disabled={disabled || busy} onChange={event => updateSaved(previous => ({ ...previous, instructions: event.target.value }))} placeholder="Make it clearer, more visual, or more suspenseful…" className={`${editorInput} mt-2`} /></label>
      <div className="flex flex-wrap items-center gap-3"><button type="button" disabled={disabled || busy || !value.trim() || value.length > 2000} onClick={generate} className="rounded-lg border border-indigo-200 px-3 py-2 text-sm font-semibold text-indigo-600 disabled:opacity-50 dark:border-indigo-800 dark:text-indigo-300">{busy ? "Rewriting…" : "Generate rewrite"}</button><p className="text-xs text-gray-500">{value.trim() ? "One paid AI request. Review before applying." : "Add a prompt first."}</p></div>
      {error && <p role="alert" className="text-sm text-red-600 dark:text-red-300">{error}</p>}
      {saved.draft && <div className="rounded-xl border border-gray-200 p-3 dark:border-gray-700">
        <p className="text-xs font-semibold">Suggested rewrite</p>
        <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-gray-600 dark:text-gray-300">{saved.draft}</p>
        {stale && <p role="status" className="mt-2 text-xs text-amber-700 dark:text-amber-300">Your prompt changed. Generate a new rewrite for the current text.</p>}
        <div className="mt-3 flex gap-4"><button type="button" disabled={disabled || busy || stale} onClick={() => { onUse(saved.draft); updateSaved(previous => ({ ...previous, draft: null, open: false })); }} className="text-sm font-semibold text-indigo-600 disabled:opacity-50 dark:text-indigo-300">Use rewrite</button><button type="button" disabled={disabled || busy} onClick={() => updateSaved(previous => ({ ...previous, draft: null }))} className="text-sm text-gray-500">Discard rewrite</button></div>
      </div>}
    </div>
  );
  if (embedded) return content;
  return <details open={saved.open} onToggle={event => {
    const open = event.currentTarget.open;
    if (open !== saved.open) updateSaved(previous => ({ ...previous, open }));
  }} className="mt-3 text-sm">
    <summary className="cursor-pointer font-medium text-indigo-600 dark:text-indigo-300">Rewrite with AI</summary>
    {content}
  </details>;
}
