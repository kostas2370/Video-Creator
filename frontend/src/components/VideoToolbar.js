import {
  HiOutlineArrowPath, HiOutlineArrowUpTray, HiOutlineClock,
  HiOutlineCog6Tooth, HiOutlinePhoto, HiOutlinePlay, HiOutlineSquares2X2,
} from "react-icons/hi2";
import { formatDuration } from "../utils/timing";

export const toolbarAction = "inline-flex min-h-10 items-center justify-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-40 dark:text-gray-300 dark:hover:bg-gray-700/60 dark:hover:text-white";
const actionFocus = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900 disabled:cursor-not-allowed disabled:opacity-40";

export function VideoToolbar({ video, sceneCount, runtime, format, statusLabel, processing,
  canPreview, canExport, renderPending, saving, isResumable,
  onPreview, onSettings, onCover, onExport, onResume, tagsAction }) {
  const exporting = renderPending || video?.status === "RENDERING";
  const exportHint = canExport ? "Export your current edit" : saving ? "Wait for your changes to save" : !sceneCount ? "Add a scene before exporting" : `Export is unavailable while ${statusLabel.toLowerCase()}`;
  const statusColor = video?.status === "FAILED" ? "bg-amber-500" : video?.status === "COMPLETED" ? "bg-emerald-500" : "bg-blue-500";

  return <div className="editor-toolbar sticky top-2 z-20 mb-5 rounded-2xl border border-gray-200/80 bg-white/95 p-2 shadow-lg shadow-gray-900/5 backdrop-blur-xl dark:border-gray-700/80 dark:bg-gray-900/95">
    <div aria-label="Video actions" className="grid grid-cols-2 items-center gap-2 sm:flex sm:flex-wrap">
      <button type="button" disabled={!canPreview} aria-label="Preview video" title={canPreview ? "Preview your saved edits" : "Preview is available after processing and saving scenes"} onClick={onPreview} className={`order-1 inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 transition-colors hover:bg-blue-100 dark:bg-blue-500/10 dark:text-blue-300 dark:hover:bg-blue-500/20 ${actionFocus}`}><HiOutlinePlay aria-hidden="true" className="h-4 w-4" />Preview</button>
      <div role="group" aria-label="Project tools" className="order-3 col-span-2 flex flex-wrap items-center justify-center gap-1 border-t border-gray-100 pt-2 sm:order-2 sm:justify-start sm:border-l sm:border-t-0 sm:pl-2 sm:pt-0 dark:border-gray-700/70">
        <button type="button" disabled={!video || video.status === "REVIEW"} aria-label="Video settings" title="Video format, narration and appearance" onClick={onSettings} className={toolbarAction}><HiOutlineCog6Tooth aria-hidden="true" className="h-4 w-4" />Settings</button>
        <button type="button" disabled={!video?.output || processing || renderPending} title={video?.output ? "Create a cover from your exported video" : "Export your video to create a cover"} onClick={onCover} className={toolbarAction}><HiOutlinePhoto aria-hidden="true" className="h-4 w-4" />Cover</button>
        {tagsAction}
        {isResumable && <button type="button" onClick={onResume} className={`${toolbarAction} text-amber-700 dark:text-amber-300`}><HiOutlineArrowPath aria-hidden="true" className="h-4 w-4" />Retry<span className="sr-only"> generation</span></button>}
      </div>
      <button type="button" disabled={!canExport} aria-label={renderPending ? "Starting export" : video?.status === "RENDERING" ? "Exporting video" : "Export video"} title={exportHint} onClick={onExport} className={`order-2 inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm shadow-blue-600/20 transition-colors hover:bg-blue-700 sm:order-3 sm:ml-auto ${actionFocus}`}>
        {exporting ? <HiOutlineArrowPath aria-hidden="true" className="h-4 w-4 motion-safe:animate-spin" /> : <HiOutlineArrowUpTray aria-hidden="true" className="h-4 w-4" />}
        {renderPending ? "Starting…" : exporting ? "Exporting…" : "Export video"}
      </button>
    </div>
    <div aria-label="Project overview" className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-gray-100 px-2 pb-1 pt-2 text-[11px] text-gray-500 dark:border-gray-700/70 dark:text-gray-400">
      <span role="status" className="inline-flex items-center gap-1.5 font-medium text-gray-700 dark:text-gray-200"><span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${statusColor} ${processing ? "motion-safe:animate-pulse" : ""}`} />{statusLabel}</span>
      <span className="inline-flex items-center gap-1.5"><HiOutlineSquares2X2 aria-hidden="true" className="h-3.5 w-3.5" />{sceneCount} {sceneCount === 1 ? "scene" : "scenes"}</span>
      <span className="inline-flex items-center gap-1.5"><HiOutlineClock aria-hidden="true" className="h-3.5 w-3.5" />{formatDuration(runtime)}</span>
      {format && <span title={`${format.label} video`}>{format.ratio}</span>}
      {saving ? <span role="status" className="inline-flex items-center gap-1.5 text-blue-600 sm:ml-auto dark:text-blue-300"><HiOutlineArrowPath aria-hidden="true" className="h-3 w-3 motion-safe:animate-spin" />Saving changes…</span> : !sceneCount && <span className="sm:ml-auto">Add a scene to get started</span>}
    </div>
  </div>;
}
