import { useEffect, useState } from "react";
import { HiOutlineDocumentText, HiOutlineSparkles } from "react-icons/hi2";
import { toolbarAction } from "./VideoToolbar";
import { VideoMetadataFields } from "./VideoMetadataFields";
import { EditorDialog, editorInput, editorButton } from "./ui/EditorDialog";
import { saveVideoDetails, draftVideoTags, draftYouTubeDescription } from "../api/apiService";
import { tagDraft, parseTagDraft, tagGroups, copyTagText } from "../utils/videoTags";
import { appendTimestamps, descriptionBytes, youtubeTagLength } from "../utils/youtubeMetadata";

const detailsOf = video => ({ title: video.title || "", description: video.description || "", tags: video.tags || {} });
const draftOf = details => ({ title: details.title, caption: details.description, ...tagDraft(details.tags) });

export function VideoDetails({ video, open, onOpenChange, onSaved }) {
  const [baseline, setBaseline] = useState(() => detailsOf(video));
  const [draft, setDraft] = useState(() => draftOf(detailsOf(video)));
  const [activeGroup, setActiveGroup] = useState("youtube");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [conflict, setConflict] = useState(null);
  const [descriptionRevision, setDescriptionRevision] = useState(null);
  const dirty = JSON.stringify(draft) !== JSON.stringify(draftOf(baseline));
  const tags = parseTagDraft(draft);
  const invalid = !draft.title.trim() || Array.from(draft.title).length > 50 || descriptionBytes(draft.caption) > 5000 || tagGroups.some(({ key }) => tags[key].length > 20 || tags[key].some(tag => Array.from(tag).length > 80));

  useEffect(() => {
    if (!dirty && !busy) {
      const latest = detailsOf(video);
      setBaseline(latest);
      setDraft(draftOf(latest));
    }
  }, [video.title, video.description, video.tags, dirty, busy]);
  useEffect(() => {
    if (!dirty) return;
    const warn = event => { event.preventDefault(); event.returnValue = ""; };
    const checkNavigation = event => {
      const link = event.target.closest?.("a[href]");
      if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target === "_blank" || link.hasAttribute("download")) return;
      const destination = new URL(link.href, window.location.href);
      if (destination.origin === window.location.origin && destination.pathname + destination.search === window.location.pathname + window.location.search) return;
      if (!window.confirm("Leave without saving your video details?")) { event.preventDefault(); event.stopPropagation(); }
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", checkNavigation, true);
    return () => { window.removeEventListener("beforeunload", warn); document.removeEventListener("click", checkNavigation, true); };
  }, [dirty]);

  const change = event => {
    const { name, value } = event.target;
    setDraft(previous => ({ ...previous, [name]: value }));
    setError(""); setMessage("");
  };
  const save = async event => {
    event.preventDefault();
    if (busy || invalid || conflict) return;
    setBusy("save"); setError("");
    const result = await saveVideoDetails(video.id, { title: draft.title, description: draft.caption, tags }, baseline);
    if (result.ok) {
      setBaseline(result.data); setDraft(draftOf(result.data)); onSaved(result.data);
      setMessage("Video details saved. Publishing will use these details.");
    } else {
      setError(result.message);
      if (result.status === 409) setConflict(result.errors?.details || detailsOf(video));
    }
    setBusy("");
  };
  const generateTags = async () => {
    if (busy) return;
    setBusy("tags"); setError("");
    const result = await draftVideoTags(video.id);
    if (result.ok) {
      setDraft(previous => ({ ...previous, ...tagDraft(result.data.tags) }));
      setMessage("Tags drafted for all platforms. Review and save your changes.");
    } else setError(result.message);
    setBusy("");
  };
  const describe = async mode => {
    if (busy) return;
    setBusy(`description-${mode}`); setError("");
    const result = await draftYouTubeDescription(video.id, mode);
    if (result.ok) {
      const next = mode === "timestamps" ? appendTimestamps(draft.caption, result.data.description) : result.data.description;
      if (descriptionBytes(next) > 5000) setError("Shorten your description before adding chapters; this draft exceeds 5,000 bytes.");
      else {
        setDescriptionRevision(draft.caption);
        setDraft(previous => ({ ...previous, caption: next }));
        setMessage("Description draft ready. Review and save your changes.");
      }
    } else setError(result.message);
    setBusy("");
  };
  const copy = async () => {
    try { await navigator.clipboard.writeText(copyTagText(activeGroup, tags[activeGroup])); setMessage("Copied tags."); }
    catch { setError("Could not copy. Select and copy the tags manually."); }
  };
  const group = tagGroups.find(row => row.key === activeGroup);

  return <>
    <button type="button" aria-haspopup="dialog" onClick={() => onOpenChange(true)} className={toolbarAction}><HiOutlineDocumentText aria-hidden="true" className="h-4 w-4" />Video details{dirty && <span aria-label="Unsaved changes" className="h-1.5 w-1.5 rounded-full bg-amber-500" />}</button>
    <EditorDialog open={open} onClose={() => onOpenChange(false)} busy={!!busy} title="Video details" description="Prepare your title, description, and discovery tags in one place." maxWidth="max-w-3xl" footer={<div className="space-y-3">
      {error && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      {message && !error && <p role="status" className="text-sm text-blue-700 dark:text-blue-300">{message}</p>}
      {conflict && <button type="button" onClick={() => { setBaseline(conflict); setDraft(draftOf(conflict)); onSaved(conflict); setConflict(null); setError(""); setDescriptionRevision(null); }} className="text-sm font-semibold text-blue-600">Discard draft and load saved details</button>}
      <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-xs text-gray-500">{dirty ? "Unsaved changes · closing keeps your draft" : "Saved with this project · ready for publishing"}</p><div className="ml-auto flex gap-2"><button type="button" disabled={!!busy} onClick={() => onOpenChange(false)} className="rounded-xl px-4 py-3 text-sm text-gray-500">Close</button><button type="submit" form="video-details-form" disabled={!dirty || !!busy || invalid || !!conflict} className={editorButton}>{busy === "save" ? "Saving…" : "Save details"}</button></div></div>
    </div>}>
      <form id="video-details-form" onSubmit={save}>
        <fieldset disabled={!!busy || !!conflict} className="space-y-6">
          <VideoMetadataFields options={draft} change={change} busy={busy} onDescription={describe} descriptionRevision={descriptionRevision} onUndoDescription={() => { setDraft(previous => ({ ...previous, caption: descriptionRevision })); setDescriptionRevision(null); }} />
          <section className="border-t border-gray-200 pt-5 dark:border-gray-700">
            <div className="flex items-center justify-between gap-3"><h3 className="font-semibold">Discovery tags</h3><button type="button" onClick={generateTags} className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold dark:border-gray-600"><HiOutlineSparkles className="h-4 w-4" />{busy === "tags" ? "Generating…" : "Generate tags"}</button></div>
            <div aria-label="Tag platform" className="my-4 flex gap-1 rounded-xl bg-gray-100 p-1 dark:bg-gray-900">{tagGroups.map(({ key, shortLabel }) => <button key={key} type="button" aria-pressed={activeGroup === key} onClick={() => setActiveGroup(key)} className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium ${activeGroup === key ? "bg-white text-blue-600 shadow-sm dark:bg-gray-700 dark:text-blue-300" : "text-gray-500"}`}>{shortLabel}</button>)}</div>
            <div className="mb-2 flex items-center justify-between gap-3"><label htmlFor="details-tags" className="text-sm font-semibold">{group.label}</label><button type="button" disabled={!tags[activeGroup].length} onClick={copy} className="text-xs font-semibold text-blue-600 disabled:opacity-40">Copy tags</button></div>
            <textarea id="details-tags" name={activeGroup} value={draft[activeGroup]} onChange={change} rows={3} maxLength={2000} className={editorInput} />
            <p className="mt-2 text-xs text-gray-500">{group.hint}</p>
            {activeGroup === "youtube" && <p className={`mt-2 text-xs ${youtubeTagLength(tags.youtube) > 500 ? "text-amber-600" : "text-gray-500"}`}>{youtubeTagLength(tags.youtube)}/500 YouTube characters · includes separators and phrase quotes. {youtubeTagLength(tags.youtube) > 500 && "Shorten these tags before uploading to YouTube."}</p>}
            <p className="mt-3 text-xs text-gray-500">Generation drafts tags for all platforms from your saved script. Nothing changes until you save.</p>
          </section>
          {invalid && <p role="alert" className="text-sm text-red-600">Use a title of 1–50 characters, a description within 5,000 bytes, and up to 20 tags per platform with 80 characters per tag.</p>}
        </fieldset>
      </form>
    </EditorDialog>
  </>;
}
