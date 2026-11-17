import { useRef, useState } from "react";
import { searchClipTranscript } from "../api/apiService";
import { formatTime } from "../utils/clips";
import { editorButton, editorInput } from "./ui/EditorDialog";

export function TranscriptClipSearch({ projectId, disabled, onCreateClip, remainingSlots = 20 }) {
  const [prompt, setPrompt] = useState("");
  const [results, setResults] = useState(null);
  const [selected, setSelected] = useState([]);
  const [added, setAdded] = useState([]);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const locked = useRef(false);
  const search = async event => {
    event.preventDefault();
    if (!prompt.trim() || locked.current) return;
    locked.current = true;
    setWorking(true); setError(""); setResults(null); setSelected([]); setAdded([]);
    try {
      const result = await searchClipTranscript(projectId, prompt.trim());
      if (result.ok) setResults(result.data.clips); else setError(result.message);
    } catch { setError("Could not search the transcript. Please retry."); }
    finally { setWorking(false); locked.current = false; }
  };
  const add = async (indices, edit = false) => {
    if (locked.current || disabled || indices.length > remainingSlots) return;
    locked.current = true;
    setWorking(true); setError("");
    try {
      for (const index of indices) {
        if (added.includes(index)) continue;
        const clip = results[index];
        const success = await onCreateClip({ title: clip.title, start: clip.start, end: clip.end }, { edit });
        if (!success) { setError("Could not add this result. Previously added clips are saved; retry the remaining results."); break; }
        setAdded(current => [...current, index]);
        setSelected(current => current.filter(value => value !== index));
      }
    } catch { setError("Could not add this result. Previously added clips are saved; retry the remaining results."); }
    finally { setWorking(false); locked.current = false; }
  };
  return <section aria-label="Find clips with AI" className="clip-search mt-6 rounded-2xl border border-blue-200 bg-blue-50/50 p-4 sm:p-6 dark:border-blue-900 dark:bg-blue-950/20">
    <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-300">Search by idea</p><h3 className="text-lg font-bold">Find clips with AI</h3>
    <form onSubmit={search} className="mt-3 space-y-3"><label className="block text-sm">Describe the moment you want<textarea required maxLength={2000} rows={2} value={prompt} onChange={event => setPrompt(event.target.value)} placeholder="Find a clip where they explain how to start a business" disabled={working || disabled} className={`${editorInput} mt-2`} /></label><p className="text-xs leading-relaxed text-gray-500">Searches the saved transcript for matching moments using your preferred clip lengths. No new transcription is needed; text-provider charges apply. Add several results here, or add a result and open its editor.</p><button type="submit" disabled={working || disabled || !prompt.trim()} className={editorButton}>{working ? "Working…" : "Find matching clips"}</button></form>
    {error && <p role="alert" className="mt-3 break-words text-sm text-red-600">{error}</p>}
    {remainingSlots === 0 && <p role="status" className="mt-3 text-sm text-gray-500">This project has 20 clips. Remove a clip before adding more results.</p>}
    {results?.length === 0 && <p role="status" className="mt-3 text-sm text-gray-500">No matching moments found. Try a different description.</p>}
    {!!results?.length && <>
      <div className="mt-4 flex flex-wrap items-center gap-3"><button type="button" disabled={working || disabled || !selected.length || selected.length > remainingSlots} onClick={() => add(selected)} className={editorButton}>Add selected ({selected.length})</button><span role="status" className="text-xs text-gray-500">{added.length} added · {remainingSlots} spaces left</span>{selected.length > remainingSlots && <span className="text-xs text-amber-600">Select up to {remainingSlots} more clips.</span>}</div>
      <ul className="mt-4 space-y-3">{results.map((clip, index) => <li key={`${clip.start}-${clip.end}-${index}`} className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"><label className="flex items-center gap-3"><input type="checkbox" aria-label={`Select ${clip.title}`} checked={selected.includes(index)} disabled={working || disabled || added.includes(index) || !remainingSlots} onChange={event => setSelected(current => event.target.checked ? [...current, index] : current.filter(value => value !== index))} /><span role="heading" aria-level={4} className="break-words font-semibold">{clip.title}</span></label><p className="mt-1 text-xs text-gray-500">{formatTime(clip.start)}–{formatTime(clip.end)}</p><p className="mt-2 break-words text-sm text-gray-500">{clip.reason}</p>{added.includes(index) ? <p className="mt-2 text-sm font-semibold text-emerald-600">Added</p> : <div className="flex flex-wrap gap-4"><button type="button" disabled={working || disabled || !remainingSlots} onClick={() => add([index])} className="mt-2 min-h-11 text-sm font-semibold text-blue-600 disabled:opacity-40">Add clip</button><button type="button" disabled={working || disabled || !remainingSlots} onClick={() => add([index], true)} className="mt-2 min-h-11 text-sm font-semibold text-blue-600 disabled:opacity-40">Add and edit clip</button></div>}</li>)}</ul>
    </>}
  </section>;
}
