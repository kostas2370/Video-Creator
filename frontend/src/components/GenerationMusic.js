import { useState } from "react";
import { AIMusicPicker } from "./AIMusicPicker";

export function GenerationMusic({ value = "", onChange, className, prompt = "", genre = "", gptModel = "" }) {
  const [searchOpen, setSearchOpen] = useState(false), [selected, setSelected] = useState(null);
  const automatic = value === "auto";
  const aiSelection = (value || "").startsWith("ai:") || (value || "").startsWith("catalog:");
  return <div>
    <AIMusicPicker open={searchOpen} onClose={() => setSearchOpen(false)} prompt={prompt} genre={genre} gptModel={gptModel} onSelected={track => { setSelected(track); onChange(track.key); }} />
    <label className="mt-2 flex cursor-pointer items-start gap-2 text-sm"><input type="checkbox" checked={automatic} onChange={event => onChange(event.target.checked ? "auto" : "")} className="mt-1 accent-blue-600" /><span>Auto-select music<span className="mt-1 block text-xs text-gray-500 dark:text-gray-400">Pick general music using your video's topic and mood.</span></span></label>
    {aiSelection ? <p className="mt-3 text-sm">{selected?.key === value ? selected.title : "AI search music selected"} <button type="button" onClick={() => onChange("")} className="ml-2 text-blue-600 underline">Clear selection</button></p> : !automatic && <input type="url" aria-label="Background music YouTube link" id="music" name="music" value={value} onChange={event => onChange(event.target.value)} className={className} placeholder="Or paste a YouTube URL (optional)" />}
    <button type="button" disabled={!prompt.trim()} onClick={() => setSearchOpen(true)} className="mt-3 text-sm font-medium text-blue-600 underline disabled:opacity-40">AI search YouTube</button>
  </div>;
}
