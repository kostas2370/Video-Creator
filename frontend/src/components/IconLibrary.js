import { useEffect, useState } from "react";
import { getIcons } from "../api/apiService";
import { useDebounce } from "../hooks/useDebounce";
import { AssetPagination } from "./ui/AssetPagination";
import { editorInput } from "./ui/EditorDialog";

export function IconLibrary({ onSelect, selectedKey, searchLabel = "Search icons", compact = false, refreshKey = 0 }) {
  const [search, setSearch] = useState("");
  const [mine, setMine] = useState(false);
  const [page, setPage] = useState(1);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const query = useDebounce(search, 250);
  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    getIcons({ search: query, page, ...(mine ? { mine: true } : {}) }).then(response => {
      if (!active) return;
      if (response.ok) setResults(response.data);
      else if (response.status === 404 && page > 1) { setPage(value => value - 1); return; }
      else { setResults(null); setError(response.message || "The icon library could not be loaded."); }
      setLoading(false);
    });
    return () => { active = false; };
  }, [query, mine, page, retry, refreshKey]);
  return <div className="space-y-3">
    <div className="flex flex-wrap items-end gap-3">
      <label className="block min-w-0 flex-1 text-sm">{searchLabel}<input type="search" value={search} placeholder="Water, battery, heart…" onChange={event => { setSearch(event.target.value); setPage(1); }} className={`${editorInput} mt-1`} /></label>
      <label className="flex items-center gap-2 py-3 text-sm"><input type="checkbox" checked={mine} onChange={event => { setMine(event.target.checked); setPage(1); }} />My icons</label>
    </div>
    {loading ? <p role="status" className="text-sm text-gray-500">Loading icons…</p> : error ? <div role="alert" className="text-sm text-red-600">{error} <button type="button" onClick={() => setRetry(value => value + 1)} className="underline">Retry</button></div> : <>
      <div role="group" aria-label={compact ? searchLabel.replace("Search", "Available") : "Available icons"} className={`grid gap-2 ${compact ? "max-h-60 grid-cols-3 overflow-y-auto" : "grid-cols-2 sm:grid-cols-4 lg:grid-cols-6"}`}>
        {results?.results.map(icon => <button key={icon.key} type="button" title={icon.description} aria-pressed={selectedKey == null ? undefined : selectedKey === icon.key} aria-label={`${icon.name} (${icon.collection})`} onClick={() => onSelect(icon)} className="flex min-w-0 flex-col items-center gap-2 rounded-xl border border-gray-200 p-3 text-xs hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-600 dark:hover:bg-gray-700">
          <img src={icon.file} alt="" loading="lazy" className={`${compact ? "h-9 w-9" : "h-14 w-14"} rounded-lg bg-slate-800 p-2`} /><span className="max-w-full break-words">{icon.name}</span>
        </button>)}
      </div>
      {results?.count === 0 && <p className="py-4 text-sm text-gray-500">{mine && !query ? "You haven’t uploaded any icons yet." : "No icons found. Try another search."}</p>}
      <AssetPagination pagination={results} loading={loading} onPage={setPage} />
    </>}
  </div>;
}
