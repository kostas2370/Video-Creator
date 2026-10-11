export function AssetPagination({ pagination, loading, onPage }) {
  if (!pagination || (!pagination.previous && !pagination.next)) return null;
  return <nav aria-label="Library pages" className="flex items-center justify-center gap-4 p-5">
    <button type="button" disabled={loading || !pagination.previous} onClick={() => onPage(pagination.previous)} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40">Previous</button>
    <span className="text-sm text-gray-500">Page {pagination.current} · {pagination.count} items</span>
    <button type="button" disabled={loading || !pagination.next} onClick={() => onPage(pagination.next)} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40">Next</button>
  </nav>;
}
