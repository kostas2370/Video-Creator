import { Link } from "react-router-dom";

export function CreationDraftNotice({ draft, onReset, pendingVideoId, disabled = false }) {
  if (!draft.key) return null;
  return <div className="mb-5 space-y-2 rounded-xl border border-gray-200 px-4 py-3 text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
    <div className="flex flex-wrap items-center justify-between gap-3"><p role="status">{draft.error || (draft.restored ? "Draft restored. Your work is saved on this browser." : "Your draft is saved automatically on this browser.")}</p><button type="button" disabled={disabled} onClick={() => { if (window.confirm("Start over and discard this browser draft? Any existing video projects will remain in My videos.")) onReset(); }} className="shrink-0 font-semibold text-indigo-600 disabled:opacity-50 dark:text-indigo-300">Start over</button></div>
    {pendingVideoId && <p>This draft already has a project. <Link to={`/videos/${encodeURIComponent(pendingVideoId)}/`} className="font-semibold text-indigo-600 underline dark:text-indigo-300">Open saved project</Link> to continue, or start over for another video.</p>}
  </div>;
}
