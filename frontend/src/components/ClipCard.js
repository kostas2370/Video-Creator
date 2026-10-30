import { HiOutlinePlay, HiOutlineArrowDownTray, HiOutlineArrowPath, HiOutlineTrash } from "react-icons/hi2";
import { ClipHashtags } from "./ClipHashtags";
import { clipBusy, clipStalled, clipStatus, formatTime } from "../utils/clips";

export function ClipCard({ projectId, clip, index, selected, active, working, busy, editorSaving, hasEditor, onSelect, onEdit, onDownload, onExport, onRemove, onHashtagsSaved, onUploadedChange }) {
  const stalled = clipBusy(clip.status) && clipStalled(clip);
  const ready = clip.status === "COMPLETED";
  return <article className={`clip-card w-[min(80vw,320px)] shrink-0 rounded-2xl lg:w-auto border p-4 transition-colors ${active ? "clip-card-active border-blue-500 bg-blue-50 shadow-sm dark:bg-blue-950/30" : "border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"}`}>
    <div className="mb-3 flex items-center justify-between gap-2"><span className="text-xs font-semibold uppercase tracking-widest text-gray-400">Clip {String(index + 1).padStart(2, "0")}</span><label className="flex min-h-8 items-center gap-2 text-xs text-gray-500"><span>Select</span><input aria-label={`Select ${clip.title}`} type="checkbox" checked={selected} disabled={working || busy || (clipBusy(clip.status) && !stalled)} onChange={event => onSelect(event.target.checked)} className="h-4 w-4 rounded accent-blue-600" /></label></div>
    <h3 className="break-words font-semibold leading-snug">{clip.title}</h3>
    <p className="mt-2 font-mono text-xs text-gray-500">{formatTime(clip.start)}–{formatTime(clip.end)} <span className="ml-2 rounded-md bg-gray-100 px-2 py-1 dark:bg-gray-700">{(clip.end - clip.start).toFixed(1)}s</span></p>
    {clip.reason && <p className="mt-3 line-clamp-2 break-words text-xs leading-relaxed text-gray-500 dark:text-gray-400">{clip.reason}</p>}
    <div className="mt-3 flex flex-wrap items-center gap-2"><span className={`rounded-full px-2.5 py-1 text-xs font-medium ${ready ? "clip-status-ready bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" : clip.status === "FAILED" || stalled ? "clip-status-attention bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-300" : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"}`}>{stalled ? "Export stalled · retry available" : clipStatus[clip.status]}</span>{active && <span className="text-xs font-semibold text-blue-600 dark:text-blue-300">Editing</span>}</div>
    <label className="mt-3 flex min-h-11 items-center gap-2 text-sm font-medium text-gray-600 dark:text-gray-300"><input aria-label={`Uploaded ${clip.title}`} type="checkbox" checked={!!clip.uploaded} disabled={working || busy || hasEditor || clipBusy(clip.status)} onChange={event => onUploadedChange(event.target.checked)} className="h-4 w-4 rounded accent-emerald-600" />Uploaded<span className="text-xs font-normal text-gray-400">Marked manually</span></label>
    {clip.error && <p role="alert" className="mt-2 text-xs text-red-600 dark:text-red-300">{clip.error}</p>}
    <button type="button" disabled={working || busy || clipBusy(clip.status) || editorSaving} aria-pressed={active} onClick={onEdit} className={`mt-4 flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border px-3 text-sm font-semibold transition-colors disabled:opacity-40 ${active ? "border-blue-500 bg-blue-600 text-white" : "border-gray-200 text-blue-600 hover:border-blue-400 hover:bg-blue-50 dark:border-gray-600 dark:text-blue-300 dark:hover:bg-gray-700"}`}><HiOutlinePlay aria-hidden="true" />Preview & edit</button>
    <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs font-semibold">
      {ready && <button disabled={working} onClick={onDownload} className="flex min-h-11 items-center gap-1.5 text-emerald-600 dark:text-emerald-300"><HiOutlineArrowDownTray aria-hidden="true" />Download</button>}
      {(!clipBusy(clip.status) || stalled) && <button disabled={working || busy || hasEditor} onClick={onExport} className="flex min-h-11 items-center gap-1.5 text-gray-600 disabled:opacity-40 dark:text-gray-300"><HiOutlineArrowPath aria-hidden="true" />{clip.status === "FAILED" || stalled ? "Retry export" : "Export"}</button>}
      <button disabled={working || busy || clipBusy(clip.status) || hasEditor} onClick={onRemove} className="ml-auto flex min-h-11 items-center gap-1.5 text-gray-400 hover:text-red-600 disabled:opacity-40"><HiOutlineTrash aria-hidden="true" />Remove</button>
    </div>
    <ClipHashtags projectId={projectId} clip={clip} disabled={busy || hasEditor || working} onSaved={onHashtagsSaved} />
  </article>;
}
