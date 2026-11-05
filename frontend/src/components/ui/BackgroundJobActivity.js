import { useLayoutEffect, useState, useSyncExternalStore } from "react";
import { Link } from "react-router-dom";
import { HiOutlineSparkles, HiOutlineCheckCircle, HiOutlineExclamationCircle } from "react-icons/hi2";
import { configureBackgroundJobs, dismissBackgroundJob, getBackgroundJobs, subscribeBackgroundJobs } from "../../api/backgroundJobs";
import { EditorDialog, editorSecondaryButton } from "./EditorDialog";
import { creationDraftOwner } from "../../utils/creationDrafts";
import useAuth from "../../hooks/useAuth";

export function useBackgroundJobSession() {
  const { user, access_token } = useAuth();
  const owner = access_token ? (creationDraftOwner(null, access_token) || creationDraftOwner(user, access_token)) : "";
  useLayoutEffect(() => { configureBackgroundJobs(owner); }, [owner]);
}
const hiddenFields = new Set(["script_hash", "asset_id", "id", "narration_status"]);
export function formatJobResult(value) {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(formatJobResult).filter(Boolean).join("\n\n");
  if (value && typeof value === "object") return Object.entries(value).filter(([key]) => !hiddenFields.has(key)).map(([key, item]) => {
    const text = formatJobResult(item);
    return text ? `${key.replace(/_/g, " ").replace(/^./, letter => letter.toUpperCase())}\n${text}` : "";
  }).filter(Boolean).join("\n\n");
  return "";
}

export function BackgroundJobActivity() {
  const jobs = useSyncExternalStore(subscribeBackgroundJobs, getBackgroundJobs, getBackgroundJobs);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState("");
  const running = jobs.filter(job => ["QUEUED", "RUNNING"].includes(job.status));
  const job = jobs.find(item => item.id === selected);
  if (!jobs.length) return null;
  const result = job?.status === "SUCCEEDED" ? formatJobResult(job.result) : "";
  const close = () => { setOpen(false); setSelected(null); setMessage(""); };
  return <>
    <button type="button" onClick={() => { setOpen(true); setSelected(null); }} aria-label={`Generation activity: ${running.length} running, ${jobs.length - running.length} finished`} className={`relative inline-flex min-h-11 items-center gap-1.5 rounded-xl px-2 text-sm font-semibold hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-500 dark:hover:bg-gray-800 ${running.length ? "text-blue-600 dark:text-blue-300" : jobs.some(item => item.status === "FAILED") ? "text-red-600 dark:text-red-300" : "text-emerald-600 dark:text-emerald-300"}`}><HiOutlineSparkles aria-hidden="true" className="h-5 w-5" /><span>{running.length || jobs.length}</span></button>
    <span role="status" className="sr-only">{running.length} generation jobs running. {jobs.length - running.length} finished.</span>
    <EditorDialog open={open} onClose={close} title={job ? job.label : "Generation activity"} description={job ? "Review this result before adding it to your work." : "You can close this window and change pages. Results stay here for 24 hours on this browser."} icon={HiOutlineSparkles} maxWidth="max-w-2xl" footer={<div className="flex justify-between gap-2">{job ? <button type="button" className={editorSecondaryButton} onClick={() => { setSelected(null); setMessage(""); }}>All activity</button> : <span />}<button type="button" className={editorSecondaryButton} onClick={close}>Done</button></div>}>
      {jobs.some(item => item.storageWarning) && <p role="alert" className="mb-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200">Browser storage is unavailable. Keep this page open to recover unsaved draft results.</p>}
      {job ? <div className="space-y-4">{job.status === "FAILED" ? <p role="alert" className="text-sm text-red-600 dark:text-red-300">{job.error}</p> : result ? <><textarea readOnly aria-label="Generated result" value={result} rows={12} className="block w-full resize-y rounded-xl border border-gray-200 p-4 text-sm leading-relaxed dark:border-gray-600 dark:bg-gray-900" /><button type="button" className={editorSecondaryButton} onClick={async () => { try { await navigator.clipboard.writeText(result); setMessage("Result copied."); } catch { setMessage("Select the result above to copy it."); } }}>Copy result</button>{message && <p role="status" className="text-sm text-gray-500">{message}</p>}</> : <p className="text-sm text-gray-500 dark:text-gray-400">This update is saved in your project.</p>}{job.path && <Link to={job.path} onClick={close} className="flex min-h-11 items-center text-sm font-semibold text-blue-600 dark:text-blue-300">Open original page →</Link>}</div> : <ul className="space-y-3">{[...jobs].reverse().map(item => {
        const active = ["QUEUED", "RUNNING"].includes(item.status);
        const Icon = active ? HiOutlineSparkles : item.status === "FAILED" ? HiOutlineExclamationCircle : HiOutlineCheckCircle;
        return <li key={item.id} className="flex items-start gap-3 rounded-2xl border border-gray-200 p-4 dark:border-gray-700"><Icon aria-hidden="true" className={`mt-0.5 h-5 w-5 shrink-0 ${active ? "text-blue-500" : item.status === "FAILED" ? "text-red-500" : "text-emerald-500"}`} /><div className="min-w-0 flex-1"><p className="text-sm font-semibold">{item.label}</p><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{item.reconnecting ? "Connection lost. Reconnecting safely…" : active ? item.status === "QUEUED" ? "Queued · You can keep working" : "Generating · You can keep working" : item.status === "FAILED" ? "Needs attention" : "Ready to review"}</p><div className="mt-2 flex flex-wrap gap-x-4">{!active && <button type="button" onClick={() => { setSelected(item.id); setMessage(""); }} className="min-h-11 text-sm font-semibold text-blue-600 dark:text-blue-300">{item.status === "FAILED" ? "View error" : "View result"}</button>}{item.path && <Link to={item.path} onClick={close} className="inline-flex min-h-11 items-center text-sm text-gray-500 dark:text-gray-300">Open page</Link>}{!active && <button type="button" onClick={() => dismissBackgroundJob(item.id)} className="min-h-11 text-sm text-gray-500 dark:text-gray-400">Dismiss</button>}</div></div></li>;
      })}</ul>}
    </EditorDialog>
  </>;
}
