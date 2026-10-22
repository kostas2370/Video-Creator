import { useEffect, useState } from "react";
import { getDeletedScenes } from "../api/apiService";

export function RecentlyDeletedScenes({ videoId, refresh, disabled, onRestore }) {
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(null);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  useEffect(() => {
    if (!open) return;
    let current = true;
    setLoading(true); setError("");
    getDeletedScenes(videoId, page).then(response => {
      if (!current) return;
      if (response.ok) {
        if (!response.data.results.length && page > 1) { setPage(1); return; }
        setResult(response.data);
      } else setError(response.message || "Could not load removed scenes.");
      setLoading(false);
    });
    return () => { current = false; };
  }, [open, videoId, page, refresh, reload]);
  const restore = async scene => {
    if (restoring || disabled) return;
    setRestoring(scene.id); setError("");
    try {
      if (await onRestore(scene.id)) setReload(value => value + 1);
      else setError("Could not restore this scene. Refresh the list and try again.");
    } finally { setRestoring(null); }
  };
  return <details className="mt-4 border-t border-gray-100 pt-4 dark:border-gray-700" open={open} onToggle={event => setOpen(event.currentTarget.open)}>
    <summary className="cursor-pointer text-sm font-semibold">Recently deleted <span className="ml-2 text-xs font-normal text-gray-500 dark:text-gray-400">Recover scenes for 7 days</span></summary>
    {open && <div className="mt-3 space-y-3">
      <p className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">Restore removed scenes with their visuals, narration, and settings. After 7 days they can no longer be restored and are permanently removed by daily cleanup. Reusable files in your Media Library are kept.</p>
      {error && <div role="alert" className="text-sm text-red-600 dark:text-red-300">{error}<button type="button" onClick={() => setReload(value => value + 1)} className="ml-2 rounded px-2 font-semibold underline">Refresh list</button></div>}
      {loading ? <p role="status" className="text-sm text-gray-500">Loading removed scenes…</p> : !error && !result?.results?.length ? <p className="py-3 text-sm text-gray-500 dark:text-gray-400">No scenes to recover.</p> : !error && <>
        <ul className="space-y-3">{result.results.map(scene => <li key={scene.id} className="flex flex-col gap-3 rounded-xl border border-gray-200 p-3 sm:flex-row sm:items-center dark:border-gray-700">
          <div className="min-w-0 flex-1"><p className="text-xs font-semibold text-gray-500 dark:text-gray-400">{scene.position ? `Scene ${scene.position}` : "Removed scene"}</p><p className="mt-1 line-clamp-2 break-words text-sm">{scene.text || "Scene without text"}</p><p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Recover before <time dateTime={scene.expires_at}>{new Date(scene.expires_at).toLocaleString()}</time></p></div>
          <button type="button" disabled={disabled || !!restoring} onClick={() => restore(scene)} className="shrink-0 rounded-lg border border-blue-200 px-3 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 disabled:opacity-40 dark:border-blue-900 dark:text-blue-300 dark:hover:bg-blue-900/20">{restoring === scene.id ? "Restoring…" : "Restore scene"}</button>
        </li>)}</ul>
        {(result.previous || result.next) && <nav aria-label="Removed scene pages" className="flex flex-wrap items-center justify-between gap-2 text-xs"><button type="button" disabled={loading || !!restoring || !result.previous} onClick={() => setPage(value => value - 1)} className="rounded-lg border px-3 py-2 disabled:opacity-40">Previous</button><span>Page {page}</span><button type="button" disabled={loading || !!restoring || !result.next} onClick={() => setPage(value => value + 1)} className="rounded-lg border px-3 py-2 disabled:opacity-40">Next</button></nav>}
      </>}
    </div>}
  </details>;
}
