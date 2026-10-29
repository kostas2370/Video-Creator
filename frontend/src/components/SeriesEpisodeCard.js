import { useEffect, useReducer, useState } from "react";
import { Link } from "react-router-dom";
import { HiOutlineArrowRight, HiOutlineBookOpen, HiOutlineChevronDown, HiOutlineSparkles } from "react-icons/hi2";
import { episodeMemoryReducer } from "../utils/series";
import { editorButton, editorInput } from "./ui/EditorDialog";

const textButton = "rounded-lg px-2 py-2 text-sm font-semibold text-blue-600 disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-300";
const statusNames = { GENERATION: "Preparing episode", REVIEW: "Review storyboard", READY: "Ready to edit", COMPLETED: "Export available", RENDERING: "Exporting", FAILED: "Needs attention" };

export function EpisodeCard({ episode, onMemorySave, onMemoryDraft, onRetry, disabled }) {
  const [{ draft: memory, baseline, sourceHash }, updateMemory] = useReducer(episodeMemoryReducer, {
    draft: episode.summary || "", baseline: episode.summary || "", sourceHash: episode.script_hash || "",
  });
  const dirty = memory !== baseline;
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [previousDraft, setPreviousDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  useEffect(() => { updateMemory({ type: "remote", value: episode.summary || "", sourceHash: episode.script_hash || "" }); }, [episode.summary, episode.script_hash]);
  const save = async () => {
    if (saving || generating || disabled || (!dirty && !episode.memory_needs_review)) return;
    setSaving(true); setError(""); setSaved(false);
    try {
      const response = await onMemorySave(episode.id, memory, baseline, sourceHash);
      if (!response.ok) throw new Error(response.message || "Could not save episode memory.");
      updateMemory({ type: "saved", value: response.data.summary, sourceHash: response.data.script_hash });
      setPreviousDraft(null);
      setSaved(true);
    } catch (reason) { setError(reason.message); }
    finally { setSaving(false); }
  };
  const generateMemory = async () => {
    if (saving || generating || disabled) return;
    setGenerating(true); setError(""); setSaved(false);
    try {
      const response = await onMemoryDraft(episode.id, memory);
      if (!response.ok) throw new Error(response.message || "Could not update episode memory.");
      setPreviousDraft({ value: memory, sourceHash });
      updateMemory({ type: "generated", value: response.data.summary, sourceHash: response.data.script_hash });
    } catch (reason) { setError(reason.message); }
    finally { setGenerating(false); }
  };
  const locked = saving || generating || disabled;
  const memoryState = dirty ? "Unsaved changes" : episode.memory_needs_review ? "Needs review" : episode.is_canon && episode.summary ? "Ready for future episodes" : "Draft memory";
  const status = episode.video_id ? statusNames[episode.status] || "Project saved" : "Video removed · memory kept";
  return <article className="overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
    <div className="p-5 sm:p-6">
      <div className="flex items-start gap-4">
        <span aria-hidden="true" className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-lg font-bold tabular-nums text-indigo-600 dark:bg-indigo-900 dark:text-indigo-300">{String(episode.number).padStart(2, "0")}</span>
        <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className="text-xs font-semibold text-gray-500 dark:text-gray-400">Episode {episode.number}</span><span className={`rounded-full px-2.5 py-1 text-xs font-medium ${episode.status === "REVIEW" ? "bg-blue-50 text-blue-700 dark:bg-blue-900 dark:text-blue-200" : episode.status === "FAILED" ? "bg-red-50 text-red-700 dark:bg-red-900 dark:text-red-200" : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-200"}`}>{status}</span></div><h3 className="mt-2 break-words text-lg font-bold">{episode.video_title || episode.idea}</h3></div>
      </div>
      {episode.video_title && <p className="mt-3 line-clamp-2 break-words text-sm leading-relaxed text-gray-500 dark:text-gray-400">{episode.idea}</p>}
      <div className="mt-4 flex flex-wrap gap-3">{episode.video_id && <Link to={`/videos/${episode.video_id}/`} className={episode.status === "REVIEW" ? `${editorButton} inline-flex items-center gap-2` : "inline-flex min-h-11 items-center gap-2 rounded-xl border border-gray-200 px-4 py-2 text-sm font-semibold transition hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-indigo-500 dark:border-gray-600 dark:hover:bg-gray-700"}>{episode.status === "REVIEW" ? "Review storyboard" : "Open episode"}<HiOutlineArrowRight aria-hidden="true" /></Link>}{episode.can_retry && <button type="button" disabled={disabled} onClick={() => onRetry(episode.id)} className={textButton}>Retry draft</button>}</div>
    </div>
    <div className="border-t border-gray-100 dark:border-gray-700">
      <button type="button" aria-expanded={memoryOpen} aria-controls={`episode-memory-${episode.id}`} onClick={() => setMemoryOpen(value => !value)} className="flex min-h-14 w-full flex-wrap items-center gap-2 px-5 py-4 text-left text-sm transition hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-indigo-500 sm:px-6 dark:hover:bg-gray-700/40">
        <HiOutlineBookOpen aria-hidden="true" className="h-4 w-4 text-gray-400" /><span className="font-semibold">Episode memory</span><span className={`ml-auto rounded-full px-2.5 py-1 text-xs ${episode.memory_needs_review || dirty ? "bg-amber-50 text-amber-800 dark:bg-amber-900 dark:text-amber-200" : "text-gray-500 dark:text-gray-400"}`}>{memoryState}</span><HiOutlineChevronDown aria-hidden="true" className={`h-4 w-4 transition ${memoryOpen ? "rotate-180" : ""}`} />
      </button>
      {!memoryOpen && episode.summary && <p className="-mt-1 line-clamp-2 break-words px-5 pb-4 text-xs leading-relaxed text-gray-500 sm:px-6 dark:text-gray-400">{episode.summary}</p>}
      <div id={`episode-memory-${episode.id}`} hidden={!memoryOpen} className="px-5 pb-5 sm:px-6">
        {episode.memory_needs_review && <p role="status" className="mb-3 rounded-xl bg-amber-50 p-3 text-sm leading-relaxed text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">The story changed. Review and save its memory before future episodes use it.</p>}
        <label className="block text-sm font-semibold">What should the next episode remember?<textarea maxLength={800} rows={4} value={memory} disabled={locked} onChange={event => { updateMemory({ type: "edit", value: event.target.value }); setSaved(false); }} className={`${editorInput} mt-2 font-normal`} aria-label={`Memory for episode ${episode.number}`} /></label>
        <div className="mt-2 flex justify-between gap-3 text-xs text-gray-500 dark:text-gray-400"><span>Keep the events, discoveries and ending.</span><span className="shrink-0">{memory.length}/800</span></div>
        {dirty && (baseline !== episode.summary || sourceHash !== episode.script_hash) && <p className="mt-3 text-xs text-amber-700 dark:text-amber-300">Saved memory or script changed. Your draft is kept. <button type="button" disabled={locked} onClick={() => { updateMemory({ type: "load", value: episode.summary || "", sourceHash: episode.script_hash || "" }); setPreviousDraft(null); setError(""); setSaved(false); }} className={textButton}>Load saved memory</button></p>}
        {episode.can_update_memory && <div className="mt-4 rounded-xl bg-gray-50 p-3 dark:bg-gray-900/50"><button type="button" disabled={locked} onClick={generateMemory} className={`${textButton} inline-flex items-center gap-2`}><HiOutlineSparkles aria-hidden="true" />{generating ? "Updating memory…" : "Update memory from current script"}</button><p className="mt-1 px-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Uses your AI text provider and current corrections. Review the draft before saving.</p></div>}
        <div className="mt-4 flex flex-wrap items-center gap-3"><button type="button" disabled={locked || (!dirty && !episode.memory_needs_review)} onClick={save} className={editorButton}>{saving ? "Saving…" : episode.memory_needs_review && !dirty ? "Confirm memory is current" : "Save memory"}</button>{previousDraft && <button type="button" disabled={locked} onClick={() => { updateMemory({ type: "generated", ...previousDraft }); setPreviousDraft(null); }} className={textButton}>Undo memory update</button>}{saved && <p role="status" className="text-xs text-green-700 dark:text-green-300">Episode memory saved.</p>}</div>
        {error && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-300">{error}</p>}
        <p className="mt-4 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Future stories use reviewed memories from the latest ten prepared episodes.</p>
      </div>
    </div>
  </article>;
}
