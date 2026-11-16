import { useEffect, useState } from "react";
import { getVideoLLMTraces } from "../api/apiService";
import { EditorDialog, editorSecondaryButton } from "./ui/EditorDialog";

function formattedResponse(raw) {
  try { return JSON.stringify(JSON.parse(raw), null, 2); } catch { return raw; }
}

export function DeveloperPrompts({ videoId, open, onClose }) {
  const [page, setPage] = useState(1);
  const [reload, setReload] = useState(0);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!open) return;
    let current = true;
    setLoading(true);
    setResult(null);
    getVideoLLMTraces(videoId, page).then(response => {
      if (current) setResult(response?.ok ? response.data : { error: true });
    }).catch(() => { if (current) setResult({ error: true }); }).finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [open, videoId, page, reload]);
  return <EditorDialog open={open} onClose={onClose} title="Developer prompts"
    description="Inspect project language model requests, retries, and raw responses."
    closeLabel="Close developer prompts" maxWidth="max-w-6xl"
    footer={<div className="flex justify-end"><button type="button" onClick={onClose} className={editorSecondaryButton}>Done</button></div>}>
    {open && <div className="mt-3 space-y-3 text-sm">
      <p className="text-gray-500 dark:text-gray-400">Newest requests appear first. Older requests made before capture was added are unavailable. Reference image contents are omitted.</p>
      <button type="button" disabled={loading} onClick={() => setReload(value => value + 1)} className="underline disabled:opacity-50">Refresh requests</button>
      {loading && <p role="status">Loading requests…</p>}
      {result?.error && <p role="alert">Requests could not be loaded. Refresh to try again.</p>}
      {result && !result.error && !result.results.length && <p>No captured requests for this project yet.</p>}
      {result?.results?.map(trace => <details key={trace.id} className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
        <summary className="cursor-pointer">{trace.model} · Attempt {trace.attempt} · {new Date(trace.created_at).toLocaleString()}{trace.validation_errors.length > 0 ? " · Needs correction" : ""}</summary>
        {trace.has_reference_image && <p className="mt-2">A reference image was included with this prompt.</p>}
        {trace.validation_errors.length > 0 && <ul className="mt-2 list-inside list-disc text-amber-700 dark:text-amber-300">{trace.validation_errors.map((error, index) => <li key={index}>{error}</li>)}</ul>}
        <div className="mt-3 grid min-w-0 gap-4 lg:grid-cols-2"><div className="min-w-0">
        <h3 className="font-semibold">Prompt sent to model</h3>
        <pre tabIndex={0} className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded bg-gray-100 p-3 text-xs dark:bg-gray-900">{trace.prompt}</pre>
        </div><div className="min-w-0"><h3 className="font-semibold">Response · JSON when available</h3>
        <pre tabIndex={0} className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded bg-gray-100 p-3 text-xs dark:bg-gray-900">{formattedResponse(trace.response) || "No response returned."}</pre>
        </div></div>
      </details>)}
      {result && !result.error && result.count > 0 && <div className="flex items-center gap-3">
        <button type="button" disabled={!result.previous || loading} onClick={() => setPage(result.previous)} className="underline disabled:opacity-50">Newer</button>
        <span>Page {result.current} · {result.count} requests</span>
        <button type="button" disabled={!result.next || loading} onClick={() => setPage(result.next)} className="underline disabled:opacity-50">Older</button>
      </div>}
    </div>}
  </EditorDialog>;
}
