import { useEffect, useRef, useState } from "react";
import { EditorDialog, editorInput, editorButton } from "./ui/EditorDialog";
import { FontPicker } from "./FontPicker";
import { previewVideoCover, saveVideoCover, downloadVideoCover } from "../api/apiService";
import { useObjectUrl } from "../hooks/useObjectUrl";
import { API_HOST } from "../endpoints";

const mediaUrl = path => /^https?:\/\//i.test(path || "") ? path : `${API_HOST}${path}`;

export function ThumbnailCreator({ open, onClose, video, onSaved }) {
  const [choices, setChoices] = useState({});
  const [preview, setPreview] = useState(null);
  const [previewKey, setPreviewKey] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [duration, setDuration] = useState(0);
  const player = useRef(null);
  const sequence = useRef(0);
  const previewUrl = useObjectUrl(preview);
  const key = JSON.stringify(choices);
  const currentPreview = previewKey === key;
  useEffect(() => {
    sequence.current += 1;
    if (open) { setChoices({ time: 0, title: video?.title || "", font: "Poppins", color: "#ffffff", position: "bottom", size: 8, background: true, ...video?.cover_settings }); setPreview(null); setPreviewKey(""); setError(""); }
  }, [open, video?.id]);
  const change = (field, value) => { setChoices(current => ({ ...current, [field]: value })); setError(""); };
  const makePreview = async () => {
    if (busy) return;
    const token = ++sequence.current;
    setBusy("preview"); setError("");
    const response = await previewVideoCover(video.id, choices);
    if (token !== sequence.current) { setBusy(""); return; }
    if (response.ok) { setPreview(response.data); setPreviewKey(key); }
    else setError(response.message || "Could not preview this frame.");
    setBusy("");
  };
  const save = async () => {
    if (busy || !currentPreview) return;
    setBusy("save"); setError("");
    const response = await saveVideoCover(video.id, choices);
    if (response.ok) { onSaved(response.data); onClose(); } else setError(response.message || "Could not save the cover.");
    setBusy("");
  };
  const download = async () => {
    setBusy("download"); setError("");
    const response = await downloadVideoCover(video.id);
    if (response.ok) {
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a"); link.href = url; link.download = `${(video.title || "video").replace(/[<>:"/\\|?*]/g, "-")}-cover.png`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } else setError(response.message);
    setBusy("");
  };
  return <EditorDialog open={open} onClose={onClose} title="Create a video cover" description="Choose a frame from your exported video, add a title, and save a PNG cover." busy={!!busy} maxWidth="max-w-5xl" footer={<div className="flex flex-wrap justify-end gap-2">{video?.cover && <button type="button" disabled={!!busy} onClick={download} className="rounded-xl border border-gray-200 px-4 py-3 text-sm dark:border-gray-600">Download saved cover</button>}<button type="button" disabled={!!busy} onClick={onClose} className="px-4 py-3 text-sm text-gray-500">Cancel</button><button type="button" disabled={!!busy || !currentPreview} onClick={save} className={editorButton}>{busy === "save" ? "Saving…" : "Save cover"}</button></div>}>
    <div className="grid items-start gap-6 md:grid-cols-2">
      <div className="min-w-0 space-y-4">
        <div><h3 className="mb-2 text-sm font-semibold">Choose your frame</h3>{video?.output && <video ref={player} src={mediaUrl(video.output)} controls preload="metadata" onLoadedMetadata={event => setDuration(event.currentTarget.duration)} className="max-h-64 w-full rounded-xl bg-black" />}<button type="button" disabled={!!busy} onClick={() => { const time = player.current?.currentTime || 0; player.current?.pause(); change("time", Math.round(time * 100) / 100); }} className="mt-2 rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-blue-600 disabled:opacity-40 dark:border-gray-600 dark:text-blue-300">Use current frame</button></div>
        <label className="block text-sm">Frame time (seconds)<input type="number" min={0} max={duration ? Math.max(0, duration - .05) : 86400} step={.1} value={choices.time ?? 0} disabled={!!busy} onChange={event => { const time = Number(event.target.value); change("time", time); if (player.current && Number.isFinite(time) && time >= 0 && time < player.current.duration) player.current.currentTime = time; }} className={`${editorInput} mt-2`} /></label>
        <div className="rounded-xl border border-gray-200 p-3 dark:border-gray-600"><p className="mb-2 text-xs font-medium">Cover preview{preview && !currentPreview ? " · Update to see your changes" : ""}</p>{previewUrl ? <img src={previewUrl} alt="Generated video cover preview" className="max-h-80 w-full object-contain" /> : <p className="py-8 text-center text-sm text-gray-500">Choose a frame and title, then preview your cover.</p>}</div>
      </div>
      <fieldset disabled={!!busy} className="min-w-0 space-y-4">
        <label className="block text-sm">Cover title<textarea maxLength={100} rows={3} value={choices.title || ""} onChange={event => change("title", event.target.value)} className={`${editorInput} mt-2`} placeholder="Leave blank for a frame-only cover" /></label>
        <FontPicker value={choices.font || "Poppins"} onChange={font => change("font", font)} />
        <div className="grid grid-cols-2 gap-3"><label className="text-sm">Placement<select value={choices.position || "bottom"} onChange={event => change("position", event.target.value)} className={`${editorInput} mt-2`}><option value="top">Top</option><option value="middle">Center</option><option value="bottom">Bottom</option></select></label><label className="text-sm">Text color<input type="color" value={choices.color || "#ffffff"} onChange={event => change("color", event.target.value)} className="mt-2 block h-10 w-full" /></label></div>
        <label className="block text-sm">Title size · {choices.size || 8}%<input type="range" min={3} max={16} value={choices.size || 8} onChange={event => change("size", Number(event.target.value))} className="mt-2 w-full accent-blue-600" /></label>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={choices.background ?? true} onChange={event => change("background", event.target.checked)} />Dark background behind the title</label>
        <button type="button" onClick={makePreview} className={editorButton}>{busy === "preview" ? "Creating preview…" : "Preview cover"}</button>
        <p className="text-xs leading-relaxed text-gray-500">Preview uses the export renderer. Long titles shrink to fit. The cover keeps the exported video’s aspect ratio.</p>
      </fieldset>
    </div>
    {error && <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-300">{error}</p>}
  </EditorDialog>;
}
