import { useEffect, useState } from "react";
import { draftClipHashtags, saveClipHashtags } from "../api/apiService";
import { copyTagText, parseTagDraft } from "../utils/videoTags";
import { editorInput } from "./ui/EditorDialog";

export function ClipHashtags({ projectId, clip, disabled, onSaved }) {
  const [text, setText] = useState(copyTagText("tiktok", clip.hashtags || []));
  const [previous, setPrevious] = useState(clip.hashtags || []);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const incoming = JSON.stringify(clip.hashtags || []);
  useEffect(() => {
    if (!dirty) { const values = JSON.parse(incoming); setText(copyTagText("tiktok", values)); setPrevious(values); }
  }, [incoming]);
  const generate = async () => {
    setBusy(true); setError(""); setMessage("");
    const result = await draftClipHashtags(projectId, clip.id);
    setBusy(false);
    if (result.ok) { setText(copyTagText("tiktok", result.data.hashtags)); setDirty(true); setMessage("Review the suggestions, then save."); }
    else setError(result.message);
  };
  const save = async () => {
    setBusy(true); setError(""); setMessage("");
    const values = parseTagDraft({ tiktok: text }).tiktok;
    const result = await saveClipHashtags(projectId, clip.id, values, previous);
    setBusy(false);
    if (result.ok) { setText(copyTagText("tiktok", result.data.hashtags)); setPrevious(result.data.hashtags); setDirty(false); setMessage("Hashtags saved."); await onSaved(); }
    else setError(result.message);
  };
  const copy = async () => {
    setError(""); setMessage("");
    try { await navigator.clipboard.writeText(copyTagText("tiktok", parseTagDraft({ tiktok: text }).tiktok)); setMessage("Hashtags copied."); }
    catch { setError("Could not copy automatically. Select and copy the hashtags above."); }
  };
  return <details className="mt-5 border-t border-gray-100 pt-4 dark:border-gray-700"><summary className="cursor-pointer text-sm font-semibold">Hashtags{clip.hashtags?.length ? ` (${clip.hashtags.length})` : ""}</summary>
    <fieldset disabled={disabled || busy} className="mt-3 min-w-0">
      <label className="block text-xs text-gray-500">Hashtags for {clip.title}<textarea aria-label={`Hashtags for ${clip.title}`} rows={3} maxLength={1700} value={text} onChange={event => { setText(event.target.value); setDirty(true); setMessage(""); }} placeholder="#Topic #SpecificTopic" className={`${editorInput} mt-2 !text-sm`} /></label>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm font-semibold"><button type="button" className="min-h-11" onClick={generate}>{busy ? "Working…" : "Generate hashtags"}</button><button type="button" disabled={!dirty} onClick={save} className="min-h-11 text-blue-600 disabled:opacity-40 dark:text-blue-300">Save hashtags</button><button type="button" className="min-h-11" disabled={!text.trim()} onClick={copy}>Copy hashtags</button>{dirty && <button type="button" className="min-h-11" onClick={() => { const values = clip.hashtags || []; setText(copyTagText("tiktok", values)); setPrevious(values); setDirty(false); setMessage(""); setError(""); }}>Load saved</button>}</div>
      <p className="mt-2 text-xs leading-relaxed text-gray-500">English hashtags, including named people and characters supported by the clip. Generation uses your text provider. Up to 20 hashtags.</p>
    </fieldset>
    {message && <p role="status" className="mt-2 text-xs text-emerald-600 dark:text-emerald-300">{message}</p>}{error && <p role="alert" className="mt-2 text-xs text-red-600 dark:text-red-300">{error}</p>}
  </details>;
}
