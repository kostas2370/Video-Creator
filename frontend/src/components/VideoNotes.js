import { RememberedDetails } from "./ui/RememberedDetails";
import { useEffect, useState } from "react";
import { HiOutlinePencilSquare } from "react-icons/hi2";
import { saveVideoNotes } from "../api/apiService";
import { editorInput, editorButton } from "./ui/EditorDialog";

export function VideoNotes({ videoId, notes = "", onSaved }) {
  const [draft, setDraft] = useState(notes);
  const [baseline, setBaseline] = useState(notes);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(null);
  const dirty = draft !== baseline;

  useEffect(() => {
    if (!dirty && !saving) { setDraft(notes); setBaseline(notes); }
  }, [notes, dirty, saving]);
  useEffect(() => {
    if (!dirty) return;
    const warn = event => { event.preventDefault(); event.returnValue = ""; };
    const checkNavigation = event => {
      const link = event.target.closest?.("a[href]");
      if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target === "_blank" || link.hasAttribute("download")) return;
      const destination = new URL(link.href, window.location.href);
      if (destination.origin !== window.location.origin || destination.pathname + destination.search === window.location.pathname + window.location.search) return;
      if (!window.confirm("Leave this video without saving your notes?")) { event.preventDefault(); event.stopPropagation(); }
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", checkNavigation, true);
    return () => { window.removeEventListener("beforeunload", warn); document.removeEventListener("click", checkNavigation, true); };
  }, [dirty]);

  const save = async () => {
    if (saving || !dirty || conflict !== null) return;
    setSaving(true); setError(""); setSaved(false);
    try {
      const response = await saveVideoNotes(videoId, draft, baseline);
      if (!response.ok) {
        if (response.status === 409) setConflict(response.errors?.notes ?? notes);
        throw new Error(response.message || "Could not save your notes. Your draft is still here.");
      }
      setBaseline(response.data.notes);
      onSaved(response.data.notes);
      setSaved(true);
    } catch (reason) { setError(reason.message || "Could not save your notes. Try again."); }
    finally { setSaving(false); }
  };

  return <RememberedDetails videoId={videoId} panel="projectNotes" className="editor-panel mb-4 rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
    <summary className="cursor-pointer text-sm font-semibold"><span className="ml-1 inline-flex items-center gap-2 align-middle"><HiOutlinePencilSquare aria-hidden="true" className="h-4 w-4 text-blue-500" />Project notes</span><span className="ml-3 text-xs font-normal text-gray-500 dark:text-gray-400">{dirty ? "Unsaved changes" : notes ? "View notes" : "Ideas, reminders & feedback"}</span></summary>
    <div className="mt-4">
      <label htmlFor="video-notes" className="block text-xs text-gray-500 dark:text-gray-400">Keep your project reminders here. Notes are saved with this video and are not included in exports.</label>
      <textarea id="video-notes" rows={5} maxLength={10000} disabled={saving} value={draft} onChange={event => { setDraft(event.target.value); setSaved(false); setError(""); }} onKeyDown={event => { if ((event.metaKey || event.ctrlKey) && event.key === "Enter") { event.preventDefault(); save(); } }} className={`${editorInput} mt-3 resize-y`} placeholder="Ideas to try, changes to make, feedback to remember…" />
      {error && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-300">{error}</p>}
      {conflict !== null && <div className="mt-3 rounded-xl border border-amber-200 p-3 text-sm dark:border-amber-700"><p>Another session saved different notes. Copy anything you need from your draft before loading the saved version.</p><button type="button" onClick={() => { if (window.confirm("Replace this draft with the latest saved notes?")) { setDraft(conflict); setBaseline(conflict); onSaved(conflict); setConflict(null); setError(""); } }} className="mt-2 font-semibold text-blue-600 dark:text-blue-300">Load saved notes</button></div>}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3"><p role="status" className="text-xs text-gray-500 dark:text-gray-400">{saving ? "Saving notes…" : dirty ? "Unsaved changes" : saved ? "Notes saved" : ""}<span className="ml-2">{draft.length.toLocaleString()}/10,000</span></p><button type="button" disabled={!dirty || saving || conflict !== null} onClick={save} className={editorButton}>{saving ? "Saving…" : "Save notes"}</button></div>
    </div>
  </RememberedDetails>;
}
