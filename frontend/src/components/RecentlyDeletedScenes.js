import { useEffect, useState } from "react";
import { getDeletedScenes } from "../api/apiService";
import { RecentlyDeletedContent } from "./RecentlyDeletedContent";

export function RecentlyDeletedScenes({ videoId, refresh, disabled, onRestore }) {
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(null);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const reloadList = () => setReload(value => value + 1);

  useEffect(() => {
    if (!open) return;
    let current = true;
    setLoading(true);
    setError("");
    const load = async () => {
      try {
        const response = await getDeletedScenes(videoId, page);
        if (!current) return;
        if (!response.ok) {
          setError(response.message || "Could not load removed scenes.");
        } else if (!response.data.results.length && page > 1) {
          setPage(1);
        } else {
          setResult(response.data);
        }
      } catch {
        if (current) setError("Could not load removed scenes. Please try again.");
      } finally {
        if (current) setLoading(false);
      }
    };
    load();
    return () => { current = false; };
  }, [open, videoId, page, refresh, reload]);

  const restore = async scene => {
    if (restoring || disabled) return;
    setRestoring(scene.id);
    setError("");
    try {
      if (await onRestore(scene.id)) reloadList();
      else setError("Could not restore this scene. Refresh the list and try again.");
    } catch {
      setError("Could not restore this scene. Please try again.");
    } finally {
      setRestoring(null);
    }
  };

  return (
    <details className="mt-4 border-t border-gray-100 pt-4 dark:border-gray-700" open={open} onToggle={event => setOpen(event.currentTarget.open)}>
      <summary className="cursor-pointer text-sm font-semibold">
        Recently deleted <span className="ml-2 text-xs font-normal text-gray-500 dark:text-gray-400">Recover scenes for 7 days</span>
      </summary>
      {open && (
        <div className="mt-3 space-y-3">
          <p className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">
            Restore removed scenes with their visuals, narration, and settings. After 7 days they can no longer be restored and are permanently removed by daily cleanup. Reusable files in your Media Library are kept.
          </p>
          <RecentlyDeletedContent
            loading={loading} error={error} result={result} page={page}
            restoring={restoring} disabled={disabled} onReload={reloadList}
            onRestore={restore} onPage={setPage}
          />
        </div>
      )}
    </details>
  );
}
