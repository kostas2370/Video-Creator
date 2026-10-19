import { FontPicker } from "./FontPicker";
import { editorToolButton } from "./ui/editorStyles";
import { useEffect, useRef, useState } from "react";
import { HiOutlineRectangleStack } from "react-icons/hi2";
import { EditorDialog, editorButton, editorInput } from "./ui/EditorDialog";
import { OverlayLayer, overlayPositions } from "./OverlayLayer";
import { updateSceneOverlays } from "../api/apiService";
import { API_HOST } from "../endpoints";
import { isVideo } from "../utils/media";

const names = { title: "Title", "lower-third": "Lower third", watermark: "Watermark", cta: "Call to action" };
const preset = kind => ({ kind, font: "DejaVu Sans", text: { title: "Your title", "lower-third": "Name · Role", watermark: "Your brand", cta: "Learn more" }[kind], logo: false, position: { title: "middle-center", "lower-third": "bottom-left", watermark: "top-right", cta: "bottom-center" }[kind], start: 0, end: null, size: kind === "watermark" ? 2 : 4, width: 20, color: "#ffffff", background: kind !== "watermark", opacity: kind === "watermark" ? 0.7 : 1 });

export function SceneOverlays({ scene, index, disabled, onSaved, videoFormat }) {
  const [open, setOpen] = useState(false);
  const trigger = useRef(null);
  const close = () => { setOpen(false); requestAnimationFrame(() => trigger.current?.focus()); };
  return <>
    <button
      ref={trigger}
      type="button"
      disabled={disabled}
      onClick={() => setOpen(true)}
      aria-label={`${scene.overlays?.length ? "Edit" : "Add"} text and logo overlays for scene ${index + 1}`}
      aria-haspopup="dialog"
      aria-expanded={open}
      title="Add titles, lower thirds, watermarks and calls to action"
      className={editorToolButton}
    >
      <HiOutlineRectangleStack aria-hidden="true" className="h-5 w-5 shrink-0" />
      <span>Text & logos</span>
      {scene.overlays?.length > 0 && <span aria-hidden="true" className="flex h-5 min-w-5 items-center justify-center rounded-full bg-blue-200 px-1 text-xs text-blue-800 dark:bg-blue-800 dark:text-blue-100">{scene.overlays.length}</span>}
    </button>
    {open && <OverlayEditor scene={scene} index={index} disabled={disabled} onSaved={onSaved} onClose={close} videoFormat={videoFormat} />}
  </>;
}

function OverlayEditor({ scene, index, disabled, onSaved, onClose, videoFormat }) {
  const [items, setItems] = useState(() => (scene.overlays || []).map(item => ({ ...item })));
  const [selected, setSelected] = useState(0);
  const [logoFile, setLogoFile] = useState(null);
  const [logoUrl, setLogoUrl] = useState(null);
  const [time, setTime] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const duration = scene.timing?.duration || 5;
  const item = items[selected];
  useEffect(() => {
    if (!logoFile) { setLogoUrl(null); return; }
    const url = URL.createObjectURL(logoFile); setLogoUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [logoFile]);
  const logo = logoUrl || scene.overlay_logo;
  const update = changes => setItems(current => current.map((row, i) => i === selected ? { ...row, ...changes } : row));
  const add = kind => { setItems(current => [...current, preset(kind)]); setSelected(items.length); setTime(0); };
  const save = async () => {
    if (busy || disabled) return;
    if (items.some(row => !row.logo && !row.text.trim())) { setError("Enter text for every text overlay."); return; }
    if (items.some(row => row.logo) && !logo) { setError("Upload a logo for the watermark."); return; }
    if (items.some(row => !Number.isFinite(row.start) || row.start < 0 || (row.end != null && (!Number.isFinite(row.end) || row.end <= row.start)))) { setError("Each overlay needs a start of zero or later and a positive duration."); return; }
    setBusy(true); setError("");
    try {
      let data = { overlays: items };
      if (logoFile) { data = new FormData(); data.append("overlays", JSON.stringify(items)); data.append("overlay_logo", logoFile); }
      const response = await updateSceneOverlays(scene.id, data);
      if (response.ok) { onSaved(true); onClose(); }
      else setError(response.message || "Could not save overlays. Check the settings and try again.");
    } catch { setError("Could not save overlays. Your changes are still here; try again."); }
    finally { setBusy(false); }
  };
  const source = scene.scene_image?.file;
  const media = source && (/^https?:\/\//i.test(source) ? source : `${API_HOST}${source}`);
  return <EditorDialog open onClose={onClose} title="Scene overlays" description={`Scene ${index + 1} · Titles, lower thirds, watermarks and calls to action.`} busy={busy} maxWidth="max-w-5xl" footer={<div className="flex justify-end gap-3"><button type="button" disabled={busy} onClick={onClose} className="rounded-xl px-4 py-3 text-sm text-gray-500 dark:text-gray-300">Cancel</button><button type="button" disabled={busy || disabled} onClick={save} className={editorButton}>{busy ? "Saving…" : "Save overlays"}</button></div>}>
    <div className="grid items-start gap-6 md:grid-cols-2">
      <div className="md:sticky md:top-0">
        <div className="relative mx-auto w-full overflow-hidden rounded-xl bg-black" style={{ aspectRatio: videoFormat === "PORTRAIT" ? "9 / 16" : videoFormat === "SQUARE" ? "1" : "16 / 9", maxWidth: videoFormat === "PORTRAIT" ? 240 : undefined }}>
          {media && (isVideo(source) ? <OverlayVideo source={media} time={time} /> : <img src={media} alt={`Scene ${index + 1}`} className="absolute inset-0 h-full w-full object-cover" />)}
          <OverlayLayer overlays={items} logo={logo} time={time} duration={duration} />
        </div>
        <label className="mt-4 block text-sm text-gray-600 dark:text-gray-300">Preview time · {time.toFixed(1)}s / {duration.toFixed(1)}s<input aria-label="Overlay preview time" type="range" min="0" max={duration} step="0.05" value={time} onChange={e => setTime(Number(e.target.value))} className="mt-2 w-full accent-blue-600" /></label>
        <p className="mt-3 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Timing starts at the beginning of this scene and includes its pause. Overlays stop at the scene boundary. Save to update the full preview, then render to export. Text appearance can vary slightly in the export.</p>
        {items.some(row => row.start >= duration) && <p role="status" className="mt-2 text-sm text-amber-700 dark:text-amber-300">An overlay starts after this scene ends and will not appear. Move its start earlier or extend the scene.</p>}
      </div>
      <fieldset disabled={busy || disabled} className="min-w-0">
        <legend className="mb-2 text-sm font-semibold text-gray-900 dark:text-white">Add an overlay</legend>
        <div className="flex flex-wrap gap-2">{Object.entries(names).map(([kind, label]) => <button type="button" key={kind} disabled={items.length >= 8} onClick={() => add(kind)} className="rounded-lg border border-gray-200 px-3 py-2 text-sm text-blue-600 disabled:opacity-40 dark:border-gray-600 dark:text-blue-300">+ {label}</button>)}</div>
        <p className="mt-2 text-xs text-gray-500">Up to eight overlays per scene.</p>
        {items.length > 0 && <label className="mt-4 block text-sm text-gray-700 dark:text-gray-200">Editing<select className={`${editorInput} mt-1`} value={selected} onChange={e => { setSelected(Number(e.target.value)); setTime(Math.min(items[Number(e.target.value)].start, duration)); }}>{items.map((row, i) => <option key={i} value={i}>{i + 1}. {names[row.kind]} · {row.logo ? "Logo" : row.text.slice(0, 25)}</option>)}</select></label>}
        {item ? <div className="mt-4 space-y-4">
          {item.kind === "watermark" && <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200"><input type="checkbox" checked={item.logo} onChange={e => update({ logo: e.target.checked })} />Use an image logo</label>}
          {item.logo ? <label className="block text-sm text-gray-700 dark:text-gray-200">Watermark logo<input type="file" accept="image/png,image/jpeg,image/webp" className="mt-2 block w-full text-sm" onChange={e => { const file = e.target.files?.[0]; if (file && file.size > 10 * 1024 * 1024) { setError("Use a logo smaller than 10 MB."); e.target.value = ""; } else { setLogoFile(file || null); setError(""); } }} /><span className="mt-1 block text-xs text-gray-500">PNG, JPEG or WebP · 10 MB maximum. Shared by logo watermarks in this scene.</span></label> : <label className="block text-sm text-gray-700 dark:text-gray-200">Text<textarea rows="3" maxLength="200" value={item.text} onChange={e => update({ text: e.target.value })} className={`${editorInput} mt-1`} /></label>}
          {!item.logo && <FontPicker value={item.font} onChange={font => update({ font })} />}
          <label className="block text-sm text-gray-700 dark:text-gray-200">Position<select value={item.position} onChange={e => update({ position: e.target.value })} className={`${editorInput} mt-1`}>{overlayPositions.map(position => <option key={position} value={position}>{position.replace("middle", "center").replace("-", " ")}</option>)}</select></label>
          <div className="grid grid-cols-2 gap-3"><label className="block text-sm text-gray-700 dark:text-gray-200">Start (seconds)<input type="number" min="0" max="86400" step="0.1" value={Number.isFinite(item.start) ? item.start : ""} onChange={e => { const start = e.target.value === "" ? NaN : Number(e.target.value); update({ start, end: item.end != null && Number.isFinite(start) && Number.isFinite(item.start) ? start + item.end - item.start : item.end }); }} className={`${editorInput} mt-1`} /></label><label className="block text-sm text-gray-700 dark:text-gray-200">Duration (seconds)<input type="number" min="0.1" max="86400" step="0.1" placeholder="To scene end" value={item.end == null ? "" : Math.round((item.end - item.start) * 100) / 100} onChange={e => update({ end: e.target.value === "" ? null : item.start + Number(e.target.value) })} className={`${editorInput} mt-1`} /></label></div>
          <label className="block text-sm text-gray-700 dark:text-gray-200">{item.logo ? "Logo width" : "Text size"} · {item.logo ? item.width : item.size}% of frame width<input type="range" min={item.logo ? 5 : 2} max={item.logo ? 50 : 8} step={item.logo ? 1 : 0.25} value={item.logo ? item.width : item.size} onChange={e => update({ [item.logo ? "width" : "size"]: Number(e.target.value) })} className="mt-2 w-full accent-blue-600" /></label>
          {!item.logo && <div className="flex flex-wrap items-center gap-4"><label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">Text color<input type="color" value={item.color} onChange={e => update({ color: e.target.value })} /></label><label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200"><input type="checkbox" checked={item.background} onChange={e => update({ background: e.target.checked })} />Black background</label></div>}
          <label className="block text-sm text-gray-700 dark:text-gray-200">Opacity · {Math.round(item.opacity * 100)}%<input type="range" min="0.1" max="1" step="0.05" value={item.opacity} onChange={e => update({ opacity: Number(e.target.value) })} className="mt-2 w-full accent-blue-600" /></label>
          <button type="button" onClick={() => { setItems(current => current.filter((_, i) => i !== selected)); setSelected(0); }} className="text-sm font-medium text-red-600 dark:text-red-400">Remove overlay</button>
        </div> : <p className="mt-5 text-sm text-gray-500 dark:text-gray-400">Choose a preset to add your first overlay.</p>}
      </fieldset>
    </div>
    {error && <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>}
  </EditorDialog>;
}

function OverlayVideo({ source, time }) {
  const ref = useRef(null);
  const seek = () => { if (ref.current && Number.isFinite(ref.current.duration)) ref.current.currentTime = Math.min(time, Math.max(0, ref.current.duration - 1 / 24)); };
  useEffect(seek, [time, source]);
  return <video ref={ref} src={source} muted playsInline preload="auto" onLoadedMetadata={seek} className="absolute inset-0 h-full w-full object-cover" />;
}
