import { useEffect, useMemo, useState } from "react";
import { getCaptionStyles } from "../api/apiService";
import { CaptionLayer } from "./CaptionLayer";
import { editorInput } from "./ui/EditorDialog";

export function CaptionStyleEditor({ preset, config, onChange, videoFormat }) {
  const [catalog, setCatalog] = useState(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setError("");
    getCaptionStyles().then(response => {
      if (!active) return;
      if (response.ok) setCatalog(response.data);
      else setError(response.message || "Could not load caption styles.");
    }).catch(() => { if (active) setError("Could not load caption styles."); });
    return () => { active = false; };
  }, [retry]);
  const custom = useMemo(() => ({ ...catalog?.custom_defaults, ...config }), [catalog, config]);
  const resolved = preset === "CUSTOM" ? custom : catalog?.presets[preset];
  const edit = (field, value) => onChange("CUSTOM", { ...config, [field]: value });
  const size = videoFormat === "PORTRAIT" ? [1080, 1920] : videoFormat === "SQUARE" ? [1080, 1080] : [1920, 1080];
  if (error) return <p role="alert" className="text-sm text-red-600">{error} <button type="button" onClick={() => setRetry(value => value + 1)} className="underline">Retry</button></p>;
  if (!catalog) return <p role="status" className="text-sm text-gray-500">Loading caption styles…</p>;
  return <div className="space-y-4">
    <label className="block text-sm font-semibold">Caption style<select value={preset} onChange={event => onChange(event.target.value, config)} className={`${editorInput} mt-2`}>
      {Object.entries(catalog.presets).map(([key, style]) => <option key={key} value={key}>{style.name}</option>)}
      <option value="CUSTOM">Custom · make your own</option>
    </select></label>
    <div className="relative h-32 overflow-hidden rounded-xl bg-gray-900" aria-label="Caption style preview"><CaptionLayer cue={{ text: "Make every word count", active_word: 2 }} size={size} config={resolved} /></div>
    {preset === "CUSTOM" && <div className="space-y-4 rounded-xl border border-gray-200 p-4 dark:border-gray-700">
      <label className="block text-sm">Style name<input maxLength={50} value={custom.name} onChange={event => edit("name", event.target.value)} className={`${editorInput} mt-1`} /></label>
      <label className="block text-sm">Font<select value={custom.font} onChange={event => edit("font", event.target.value)} className={`${editorInput} mt-1`}>{catalog.fonts.map(font => <option key={font}>{font}</option>)}</select></label>
      <label className="block text-sm">Text size · {custom.font_size}%<input type="range" min={1} max={15} step={0.25} value={custom.font_size} onChange={event => edit("font_size", Number(event.target.value))} className="mt-2 w-full accent-blue-600" /></label>
      <div className="grid grid-cols-3 gap-3">{[["color", "Text color"], ["highlight_color", "Highlight color"], ["outline_color", "Outline color"]].map(([field, label]) => <label key={field} className="block text-xs">{label}<input aria-label={label} type="color" value={custom[field]} onChange={event => edit(field, event.target.value)} className="mt-2 h-10 w-full" /></label>)}</div>
      <label className="block text-sm">Outline width · {custom.outline_width}%<input type="range" min={0} max={1.5} step={0.05} value={custom.outline_width} onChange={event => edit("outline_width", Number(event.target.value))} className="mt-2 w-full accent-blue-600" /></label>
      <label className="block text-sm">Position<select value={custom.position} onChange={event => edit("position", event.target.value)} className={`${editorInput} mt-1`}><option value="bottom">Lower area</option><option value="middle">Center</option><option value="top">Upper area</option></select></label>
      <div className="flex flex-wrap gap-4">{[["bold", "Bold"], ["uppercase", "Uppercase"], ["highlight_words", "Word highlights"]].map(([field, label]) => <label key={field} className="inline-flex items-center gap-2 text-sm"><input type="checkbox" checked={custom[field]} onChange={event => edit(field, event.target.checked)} />{label}</label>)}</div>
      <label className="block text-sm">Words per phrase<input type="number" min={1} max={15} value={custom.max_words} onChange={event => edit("max_words", event.target.value === "" ? "" : Number(event.target.value))} className={`${editorInput} mt-1`} /></label>
      <p className="text-xs leading-relaxed text-gray-500">This style is saved with your video. Caption words and timing stay editable in each scene.</p>
    </div>}
  </div>;
}
