import { useRef, useState } from "react";
import { editorButton, editorInput } from "./ui/EditorDialog";

export function SceneTextEditor({ scene, index, manual, draft, onDraftChange, onSave, onRewrite, disabled }) {
  const [busy, setBusy] = useState(""), [error, setError] = useState("");
  const [prompt, setPrompt] = useState("");
  const running = useRef(false);
  const saved = scene.text || "";
  const text = draft?.text ?? saved;
  const changed = text !== saved;
  const conflict = changed && draft?.before !== saved;
  const locked = disabled || !!busy;
  const change = value => {
    setError("");
    onDraftChange(scene.id, value === saved ? null : { before: draft?.before ?? saved, text: value });
  };
  const discard = () => { if (!locked) { onDraftChange(scene.id, null); setError(""); } };
  const run = async action => {
    if (running.current || locked || conflict) return;
    if (action === "save" && (!changed || text.length > 2000 || (!manual && !text.trim()))) return;
    if (action === "rewrite" && (changed || !prompt.trim())) return;
    running.current = true; setBusy(action); setError("");
    try {
      if (action === "save") {
        if (!await onSave(scene, text)) throw new Error("Could not save this text. Your draft is still here.");
        onDraftChange(scene.id, null);
      } else {
        const rewritten = await onRewrite(scene, prompt);
        if (typeof rewritten !== "string") throw new Error("Could not create a rewrite. Please try again.");
        if (rewritten.length > 2000) throw new Error("The rewrite is too long. Ask for a version under 2,000 characters.");
        onDraftChange(scene.id, { before: saved, text: rewritten });
      }
    } catch (reason) { setError(reason.message); }
    finally { running.current = false; setBusy(""); }
  };
  return <section aria-label={`Scene ${index + 1} text editor`}>
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <label htmlFor={`scene-text-${scene.id}`} className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">{manual ? "Scene text" : "Script & narration"}</label>
      <span role="status" className={`text-xs ${changed ? "text-amber-700 dark:text-amber-300" : "text-gray-500 dark:text-gray-400"}`}>{busy === "save" ? "Saving…" : busy === "rewrite" ? "Writing a draft…" : changed ? "Unsaved text" : "Saved"}</span>
    </div>
    <textarea id={`scene-text-${scene.id}`} aria-label={manual ? `Text for scene ${index + 1}` : `Script for scene ${index + 1}`} rows={6} maxLength={2000} placeholder={manual ? "Add caption text…" : "Write this scene’s script…"} value={text} disabled={locked} onChange={event => change(event.target.value)} onKeyDown={event => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") { event.preventDefault(); run("save"); }
      if (event.key === "Escape" && changed && !locked) { event.preventDefault(); discard(); }
    }} className={`${editorInput} resize-y leading-7`} />
    <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-500 dark:text-gray-400"><span>{manual ? "Save to update captions." : "Saving updates the script and regenerates narration when enabled."}</span><span>{text.length}/2000</span></div>
    {conflict && <p role="alert" className="mt-3 text-xs leading-relaxed text-amber-700 dark:text-amber-300">The saved text changed while you were editing. Choose which version to keep.</p>}
    {error && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <button type="button" disabled={locked || conflict || !changed || text.length > 2000 || (!manual && !text.trim())} onClick={() => run("save")} className={`${editorButton} !px-4 !py-2 text-sm`}>{busy === "save" ? "Saving…" : "Save text"}</button>
      {conflict && <button type="button" disabled={locked} onClick={() => onDraftChange(scene.id, { before: saved, text })} className="rounded-lg px-3 py-2 text-sm font-semibold text-amber-700 hover:bg-amber-50 dark:text-amber-300 dark:hover:bg-gray-700">Keep my draft</button>}
      {changed && <button type="button" disabled={locked} onClick={discard} className="rounded-lg px-3 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100 disabled:opacity-40 dark:text-gray-300 dark:hover:bg-gray-700">{conflict ? "Use saved text" : "Discard changes"}</button>}
      <span className="text-xs text-gray-400">Ctrl / ⌘ + Enter to save</span>
    </div>
    {onRewrite && <details className="mt-4 rounded-xl border border-gray-200 p-3 dark:border-gray-700"><summary className="cursor-pointer text-sm font-medium text-blue-600 dark:text-blue-300">Rewrite with AI</summary><p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">{changed ? "Save or discard your text changes before rewriting." : "Describe your changes. Review the draft here before saving it."}</p><label className="mt-3 block text-xs font-medium text-gray-600 dark:text-gray-300">Rewrite instructions<textarea rows={2} maxLength={2000} value={prompt} disabled={locked || changed} onChange={event => setPrompt(event.target.value)} placeholder="Make it shorter and more conversational…" className={`${editorInput} mt-2`} /></label><button type="button" disabled={locked || changed || !prompt.trim()} onClick={() => run("rewrite")} className="mt-2 rounded-lg px-3 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 disabled:opacity-40 dark:text-blue-300 dark:hover:bg-gray-700">{busy === "rewrite" ? "Writing…" : "Generate rewrite"}</button></details>}
  </section>;
}
