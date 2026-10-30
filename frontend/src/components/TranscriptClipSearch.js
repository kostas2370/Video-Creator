import { useState } from "react";
import { searchClipTranscript } from "../api/apiService";
import { formatTime } from "../utils/clips";
import { editorButton, editorInput } from "./ui/EditorDialog";

export function TranscriptClipSearch({ projectId, disabled, onCreateClip }) {
  const [prompt, setPrompt] = useState("");
  const [results, setResults] = useState(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const search = async event => {
    event.preventDefault();
    if (!prompt.trim()) return;
    setWorking(true); setError(""); setResults(null);
    try {
      const result = await searchClipTranscript(projectId, prompt.trim());
      if (result.ok) setResults(result.data.clips); else setError(result.message);
    } catch { setError("Could not search the transcript. Please retry."); }
    finally { setWorking(false); }
  };
  return <section aria-label="Find clips with AI" className="mt-5 border-t border-gray-200 pt-5 dark:border-gray-700">
    <h3 className="font-semibold">Find clips with AI</h3>
    <form onSubmit={search} className="mt-3 space-y-3"><label className="block text-sm">Describe the moment you want<textarea required maxLength={2000} rows={2} value={prompt} onChange={event => setPrompt(event.target.value)} placeholder="Find a clip where they explain how to start a business" disabled={working || disabled} className={`${editorInput} mt-2`} /></label><p className="text-xs leading-relaxed text-gray-500">Searches the saved transcript for matching moments using your preferred clip lengths. No new transcription is needed; text-provider charges apply. Review each result before adding it.</p><button type="submit" disabled={working || disabled || !prompt.trim()} className={editorButton}>{working ? "Finding matching moments…" : "Find matching clips"}</button></form>
    {error && <p role="alert" className="mt-3 break-words text-sm text-red-600">{error}</p>}
    {results?.length === 0 && <p role="status" className="mt-3 text-sm text-gray-500">No matching moments found. Try a different description.</p>}
    {!!results?.length && <ul className="mt-4 space-y-3">{results.map((clip, index) => <li key={`${clip.start}-${clip.end}-${index}`} className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"><h4 className="break-words font-semibold">{clip.title}</h4><p className="mt-1 text-xs text-gray-500">{formatTime(clip.start)}–{formatTime(clip.end)}</p><p className="mt-2 break-words text-sm text-gray-500">{clip.reason}</p><button type="button" disabled={working || disabled} onClick={() => onCreateClip({ title: clip.title, start: clip.start, end: clip.end })} className="mt-2 min-h-11 text-sm font-semibold text-blue-600 disabled:opacity-40">Add and edit clip</button></li>)}</ul>}
  </section>;
}
