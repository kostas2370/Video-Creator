import { useEffect, useRef, useState } from "react";
import { draftNarration } from "../api/apiService";
import { editorInput, editorSecondaryButton } from "./ui/EditorDialog";

export function NarrationSetup({ video, disabled, onChange, onBusyChange }) {
  const sources = (video.scenes || []).map(scene => ({
    scene_id: String(scene.id), before: scene.text || "",
    before_visual: scene.scene_image?.prompt || scene.starting_frame_description || scene.text || "",
  }));
  const sourceKey = JSON.stringify(sources);
  const [rows, setRows] = useState(null), [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  const request = useRef(0), running = useRef(false);
  useEffect(() => {
    request.current += 1; running.current = false;
    setRows(null); setReviewed(false); setBusy(false); setError("");
    onChange(null); onBusyChange(false);
    return () => { request.current += 1; onBusyChange(false); };
  }, [video.id, sourceKey, onChange, onBusyChange]);
  const valid = rows?.length === sources.length && rows.every(row => row.text.trim() && row.text.length <= 2000);
  const update = next => { setRows(next); setReviewed(false); onChange(null); setError(""); };
  const write = async () => {
    if (disabled || running.current) return;
    running.current = true;
    const version = ++request.current;
    setBusy(true); onBusyChange(true); setError("");
    try {
      const result = await draftNarration(video.id);
      if (version !== request.current) return;
      if (!result.ok) throw new Error(result.message || "Could not write narration. Please try again.");
      const next = result.data?.scenes;
      if (!Array.isArray(next) || next.length !== sources.length || next.some((row, i) =>
        row.scene_id !== sources[i].scene_id || row.before !== sources[i].before || row.before_visual !== sources[i].before_visual || typeof row.text !== "string"
      )) throw new Error("The project changed while writing. Reopen settings and try again.");
      update(next);
    } catch (reason) { if (version === request.current) setError(reason.message); }
    finally {
      if (version === request.current) { running.current = false; setBusy(false); onBusyChange(false); }
    }
  };
  if (!sources.length) return null;
  return <section aria-label="Review narration" className="mt-4 rounded-xl border border-blue-200 p-4 dark:border-blue-800">
    <h4 className="text-sm font-semibold">Prepare narration before generating speech</h4>
    <p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Scene descriptions tell the video provider what to show. Narration is what the audience hears. Choose a starting point, then review each line.</p>
    <div className="mt-3 flex flex-wrap gap-2">
      <button type="button" disabled={disabled || busy} onClick={write} className={editorSecondaryButton}>{busy ? "Writing narration…" : "Write narration from scenes"}</button>
      <button type="button" disabled={disabled || busy} onClick={() => update(sources.map(row => ({ ...row, text: row.before })))} className={editorSecondaryButton}>Use existing text</button>
    </div>
    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">AI drafting uses your writing provider. Speech is generated only after you review and save.</p>
    {error && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
    {rows && <div className="mt-4 space-y-4">{rows.map((row, index) => <div key={row.scene_id} className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
      <h5 className="text-sm font-semibold">Scene {index + 1}</h5>
      <div className="mt-2 grid gap-3 sm:grid-cols-2">
        <div><p className="text-xs font-semibold text-gray-500 dark:text-gray-400">Visual description</p><p className="mt-2 whitespace-pre-wrap break-words text-xs leading-relaxed text-gray-500 dark:text-gray-400">{row.before_visual || "No visual description saved."}</p></div>
        <label className="text-xs font-semibold">Narration text<textarea aria-label={`Narration for scene ${index + 1}`} rows={4} maxLength={2000} disabled={disabled || busy} value={row.text} onChange={event => update(rows.map((item, i) => i === index ? { ...item, text: event.target.value } : item))} className={`${editorInput} mt-2 font-normal`} /></label>
      </div>
      {row.text.trim() && row.text.trim() === row.before_visual.trim() && <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">This matches the visual description. Rewrite it as spoken narration before saving.</p>}
    </div>)}
      <label className="flex items-start gap-3 text-sm"><input type="checkbox" checked={reviewed} disabled={disabled || busy || !valid} onChange={event => { setReviewed(event.target.checked); onChange(event.target.checked ? rows : null); }} className="mt-1" />I reviewed the narration for every scene and am ready to generate speech.</label>
    </div>}
  </section>;
}
