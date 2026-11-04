import { useEffect, useState } from "react";
import { getIcons } from "../api/apiService";
import { useDebounce } from "../hooks/useDebounce";
import { useIconFiles } from "../hooks/useIconFiles";
import { IconUpload } from "./IconUpload";
import { AssetPagination } from "./ui/AssetPagination";

export function DiagramIconPicker({ value = "", onChange, index }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const query = useDebounce(search, 250);
  const selected = useIconFiles([value])[value];
  useEffect(() => {
    if (!open) return;
    let active = true;
    setLoading(true); setError("");
    getIcons({ search: query, page }).then(response => {
      if (!active) return;
      if (response.ok) setResults(response.data);
      else { setResults(null); setError(response.message || "The icon library could not be loaded."); }
      setLoading(false);
    });
    return () => { active = false; };
  }, [open, query, page, retry]);
  const choose = key => { onChange(key); setOpen(false); };
  return <div>
    <button type="button" aria-expanded={open} aria-label={`Icon for item ${index + 1}: ${selected?.name || (value ? "Selected icon" : "None")}`} onClick={() => setOpen(current => !current)} className="flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600">
      {selected && <img src={selected.file} alt="" className="h-8 w-8 rounded bg-slate-800 p-1" />}
      Icon: {selected?.name || (value ? "Selected icon" : "None")}
    </button>
    {open && <div className="mt-2 space-y-2 rounded-lg border border-gray-200 p-3 dark:border-gray-600">
      <label className="block text-sm">Search icons for item {index + 1}<input value={search} placeholder="Water, battery, heart…" onChange={event => { setSearch(event.target.value); setPage(1); }} className="mt-1 w-full rounded-lg border border-gray-300 bg-white p-2 dark:border-gray-600 dark:bg-gray-900" /></label>
      <button type="button" onClick={() => choose("")} className="text-sm text-blue-600 dark:text-blue-300">No icon</button>
      <IconUpload index={index} onUploaded={icon => choose(icon.key)} />
      {loading ? <p role="status" className="text-sm text-gray-500">Loading icons…</p> : error ? <div role="alert" className="text-sm text-red-600">{error} <button type="button" onClick={() => setRetry(value => value + 1)} className="underline">Retry</button></div> : <>
        <div role="group" aria-label={`Available icons for item ${index + 1}`} className="grid max-h-60 grid-cols-3 gap-2 overflow-y-auto">
          {results?.results.map(icon => <button key={icon.key} type="button" title={icon.description} aria-pressed={value === icon.key} aria-label={`${icon.name} (${icon.collection})`} onClick={() => choose(icon.key)} className="flex flex-col items-center gap-1 rounded-lg border border-gray-200 p-2 text-xs hover:bg-blue-50 dark:border-gray-600 dark:hover:bg-gray-700">
            <img src={icon.file} alt="" loading="lazy" className="h-9 w-9 rounded bg-slate-800 p-1" /><span>{icon.name}</span>
          </button>)}
        </div>
        {results?.count === 0 && <p className="text-sm text-gray-500">No icons found. Try another search.</p>}
        <AssetPagination pagination={results} loading={loading} onPage={setPage} />
      </>}
    </div>}
  </div>;
}
