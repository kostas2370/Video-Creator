export function MoreAssetOptions({ options, label }) {
  if (!options.hasMore && !options.failed) return null;
  return <button type="button" disabled={options.loading} onClick={options.loadMore} className="mt-2 text-xs font-semibold text-blue-600 disabled:opacity-50 dark:text-blue-400">
    {options.loading ? "Loading…" : options.failed ? `Retry loading ${label}` : `Load more ${label}`}
  </button>;
}
