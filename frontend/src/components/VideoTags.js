import { useEffect, useState } from "react";
import { toolbarAction } from "./VideoToolbar";
import { HiOutlineHashtag } from "react-icons/hi2";
import { generateVideoTags, saveVideoTags } from "../api/apiService";
import { copyTagText, parseTagDraft, tagDraft, tagGroups } from "../utils/videoTags";
import { EditorDialog, editorInput, editorButton } from "./ui/EditorDialog";

const EMPTY_TAGS = {};

export function VideoTags({ videoId, tags = EMPTY_TAGS, onSaved }) {
  const [open, setOpen] = useState(false);
  const [activeGroup, setActiveGroup] = useState("tiktok");
  const [baseline, setBaseline] = useState(tags);
  const [draft, setDraft] = useState(() => tagDraft(tags));
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(null);
  const dirty = JSON.stringify(draft) !== JSON.stringify(tagDraft(baseline));
  const parsed = parseTagDraft(draft);
  const invalid = tagGroups.some(({ key }) => parsed[key].length > 20 || parsed[key].some(tag => tag.length > 80));

  useEffect(() => {
    if (!dirty && !busy) { setBaseline(tags); setDraft(tagDraft(tags)); }
  }, [tags, dirty, busy]);
  useEffect(() => {
    if (!dirty) return;
    const warn = event => { event.preventDefault(); event.returnValue = ""; };
    const checkNavigation = event => {
      const link = event.target.closest?.("a[href]");
      if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target === "_blank" || link.hasAttribute("download")) return;
      const destination = new URL(link.href, window.location.href);
      if (destination.origin !== window.location.origin || destination.pathname + destination.search === window.location.pathname + window.location.search) return;
      if (!window.confirm("Leave this video without saving your tags?")) { event.preventDefault(); event.stopPropagation(); }
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", checkNavigation, true);
    return () => { window.removeEventListener("beforeunload", warn); document.removeEventListener("click", checkNavigation, true); };
  }, [dirty]);

  const submit = async generate => {
    if (busy || conflict !== null || (generate && dirty) || (!generate && invalid)) return;
    setBusy(generate ? "generate" : "save"); setError(""); setMessage("");
    try {
      const response = generate ? await generateVideoTags(videoId, baseline) : await saveVideoTags(videoId, parsed, baseline);
      if (!response.ok) {
        if (response.status === 409) setConflict(response.errors?.tags ?? tags);
        throw new Error(response.message || "Could not save tags. Please try again.");
      }
      setBaseline(response.data.tags); setDraft(tagDraft(response.data.tags));
      onSaved(response.data.tags);
      setMessage(generate ? "Tags generated and saved. You can edit them below." : "Tags saved.");
    } catch (reason) { setError(reason.message || "Could not generate tags. Please try again."); }
    finally { setBusy(""); }
  };
  const copy = async key => {
    try {
      await navigator.clipboard.writeText(copyTagText(key, parsed[key]));
      setMessage("Copied to clipboard."); setError("");
    } catch { setError("Could not copy. Select the tags in the field and copy them manually."); }
  };

  const group = tagGroups.find(item => item.key === activeGroup);
  const hasTags = tagGroups.some(({ key }) => baseline[key]?.length);

  return <>
    <button type="button" aria-label="Video tags" aria-haspopup="dialog" title="Generate and copy tags for publishing" onClick={() => setOpen(true)} className={toolbarAction}>
      <HiOutlineHashtag aria-hidden="true" className="h-4 w-4" />Tags{dirty && <span aria-label="Unsaved changes" className="h-1.5 w-1.5 rounded-full bg-amber-500" />}
    </button>
    <EditorDialog open={open} onClose={() => setOpen(false)} title="Video tags" description="English tags for discovery, tailored to your video." busy={!!busy} maxWidth="max-w-xl" footer={
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p role="status" className="text-xs text-gray-500 dark:text-gray-400">{dirty ? "Unsaved changes" : message}</p>
        <div className="ml-auto flex gap-2">
          <button type="button" disabled={!!busy || dirty || conflict !== null} onClick={() => submit(true)} className="rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700">{busy === "generate" ? "Generating…" : hasTags ? "Regenerate" : "Generate tags"}</button>
          <button type="button" disabled={!dirty || !!busy || invalid || conflict !== null} onClick={() => submit(false)} className={editorButton}>{busy === "save" ? "Saving…" : "Save changes"}</button>
        </div>
      </div>
    }>
      <div aria-label="Tag platform" className="mb-5 flex gap-1 rounded-xl bg-gray-100 p-1 dark:bg-gray-900">
        {tagGroups.map(({ key, shortLabel }) => <button key={key} type="button" aria-pressed={activeGroup === key} onClick={() => setActiveGroup(key)} className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium ${activeGroup === key ? "bg-white text-blue-600 shadow-sm dark:bg-gray-700 dark:text-blue-300" : "text-gray-500 dark:text-gray-400"}`}>{shortLabel}</button>)}
      </div>
      <div className="mb-2 flex items-center justify-between gap-3">
        <label htmlFor={`video-tags-${activeGroup}`} className="text-sm font-semibold text-gray-900 dark:text-white">{group.label}</label>
        <button type="button" disabled={!parsed[activeGroup].length || !!busy} onClick={() => copy(activeGroup)} className="text-xs font-semibold text-blue-600 disabled:opacity-40 dark:text-blue-300">Copy {activeGroup === "tiktok" ? "hashtags" : "tags"}</button>
      </div>
      <textarea id={`video-tags-${activeGroup}`} aria-describedby="video-tags-hint" rows={5} maxLength={2000} disabled={!!busy} value={draft[activeGroup]} onChange={event => { setDraft(current => ({ ...current, [activeGroup]: event.target.value })); setMessage(""); setError(""); }} className={`${editorInput} resize-y`} placeholder={activeGroup === "tiktok" ? "Generate hashtags for this video's audience…" : "Generate search phrases for this video…"} />
      <p id="video-tags-hint" className="mt-2 text-xs text-gray-500 dark:text-gray-400">{group.hint}</p>
      <p className="mt-4 text-xs text-gray-500 dark:text-gray-400">Generate from your current script. Existing tags stay as saved until you regenerate.</p>
      {invalid && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-300">Use up to 20 tags per group, with up to 80 characters per tag.</p>}
      {error && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-300">{error}</p>}
      {conflict !== null && <button type="button" className="mt-3 text-sm font-semibold text-blue-600 dark:text-blue-300" onClick={() => { if (!dirty || window.confirm("Replace your draft with the latest saved tags?")) { setBaseline(conflict); setDraft(tagDraft(conflict)); onSaved(conflict); setConflict(null); setError(""); } }}>Load saved tags</button>}
      {dirty && <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">Save your edits before regenerating. Closing keeps your draft.</p>}
    </EditorDialog>
  </>;
}
