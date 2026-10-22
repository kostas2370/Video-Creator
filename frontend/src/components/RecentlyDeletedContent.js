function RecoverySceneCard({ scene, disabled, restoring, onRestore }) {
  return (
    <li className="flex flex-col gap-3 rounded-xl border border-gray-200 p-3 sm:flex-row sm:items-center dark:border-gray-700">
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-gray-500 dark:text-gray-400">
          {scene.position ? `Scene ${scene.position}` : "Removed scene"}
        </p>
        <p className="mt-1 line-clamp-2 break-words text-sm">{scene.text || "Scene without text"}</p>
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          Recover before <time dateTime={scene.expires_at}>{new Date(scene.expires_at).toLocaleString()}</time>
        </p>
      </div>
      <button
        type="button"
        disabled={disabled || !!restoring}
        onClick={() => onRestore(scene)}
        className="shrink-0 rounded-lg border border-blue-200 px-3 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 disabled:opacity-40 dark:border-blue-900 dark:text-blue-300 dark:hover:bg-blue-900/20"
      >
        {restoring === scene.id ? "Restoring…" : "Restore scene"}
      </button>
    </li>
  );
}

function RecoveryPagination({ result, page, restoring, onPage }) {
  if (!result.previous && !result.next) return null;
  const buttonClass = "rounded-lg border px-3 py-2 disabled:opacity-40";
  return (
    <nav aria-label="Removed scene pages" className="flex flex-wrap items-center justify-between gap-2 text-xs">
      <button type="button" disabled={!!restoring || !result.previous} onClick={() => onPage(page - 1)} className={buttonClass}>Previous</button>
      <span>Page {page}</span>
      <button type="button" disabled={!!restoring || !result.next} onClick={() => onPage(page + 1)} className={buttonClass}>Next</button>
    </nav>
  );
}

export function RecentlyDeletedContent({ loading, error, result, page, restoring, disabled, onReload, onRestore, onPage }) {
  if (loading) return <p role="status" className="text-sm text-gray-500">Loading removed scenes…</p>;
  if (error) {
    return (
      <div role="alert" className="text-sm text-red-600 dark:text-red-300">
        {error}
        <button type="button" onClick={onReload} className="ml-2 rounded px-2 font-semibold underline">Refresh list</button>
      </div>
    );
  }
  if (!result?.results?.length) {
    return <p className="py-3 text-sm text-gray-500 dark:text-gray-400">No scenes to recover.</p>;
  }
  return (
    <>
      <ul className="space-y-3">
        {result.results.map(scene => (
          <RecoverySceneCard key={scene.id} scene={scene} disabled={disabled} restoring={restoring} onRestore={onRestore} />
        ))}
      </ul>
      <RecoveryPagination result={result} page={page} restoring={restoring} onPage={onPage} />
    </>
  );
}
