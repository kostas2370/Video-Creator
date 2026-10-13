import { useEffect, useState } from "react";
import { Dialog, DialogBackdrop, DialogPanel, DialogTitle, Description } from "@headlessui/react";
import { HiOutlineXMark } from "react-icons/hi2";
import { updateMusicAudio } from "../api/apiService";

export function MusicAudio({ video, disabled, onSaved }) {
  const [values, setValues] = useState({});
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  const savedSettings = JSON.stringify(video?.settings || {});
  useEffect(() => { const s = JSON.parse(savedSettings); setValues({ music_ducking: s.music_ducking ?? false, music_volume: s.music_volume ?? 0.07, music_fade_in: s.music_fade_in ?? 2, music_fade_out: s.music_fade_out ?? 2, duck_level: s.duck_level ?? 0.25, duck_attack: s.duck_attack ?? 0.2, duck_release: s.duck_release ?? 0.8 }); }, [savedSettings]);
  if (!video?.music) return null;
  const change = (key, value) => setValues(current => ({ ...current, [key]: value }));
  const save = async () => {
    if (busy || disabled) return;
    setBusy(true); setError("");
    try { const response = await updateMusicAudio(video.id, values); if (response.ok) onSaved(); else setError(response.message || "Could not save music settings."); }
    catch { setError("Could not save music settings."); }
    finally { setBusy(false); }
  };
  return <section aria-label="Background music settings" className="mt-5 border-t border-gray-100 pt-4 dark:border-gray-700">
    <h3 className="text-sm font-semibold">Background music</h3>
    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Volume, fades and automatic ducking.</p>
    <button type="button" disabled={disabled} aria-haspopup="dialog" onClick={() => setOpen(true)} className="mt-2 text-xs font-semibold text-blue-600 disabled:opacity-40 dark:text-blue-400">Edit music</button>
    <Dialog open={open} onClose={() => setOpen(false)} className="relative z-50">
      <DialogBackdrop className="fixed inset-0 bg-gray-950/70 backdrop-blur-sm" />
      <div className="fixed inset-0 flex items-center justify-center p-3 sm:p-6">
        <DialogPanel className="flex max-h-[calc(100dvh-1.5rem)] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl dark:border-gray-700 dark:bg-gray-900 sm:max-h-[calc(100dvh-3rem)]">
          <header className="flex shrink-0 items-start justify-between gap-4 border-b border-gray-100 px-4 py-4 dark:border-gray-800 sm:px-6">
            <div><DialogTitle className="text-lg font-semibold text-gray-900 dark:text-white">Background music</DialogTitle><Description className="mt-1 text-sm text-gray-500 dark:text-gray-400">Balance music with your voiceover and soften the beginning and ending.</Description></div>
            <button type="button" data-autofocus aria-label="Close music editor" onClick={() => setOpen(false)} className="rounded-full p-2 text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:hover:bg-gray-800"><HiOutlineXMark className="h-5 w-5" /></button>
          </header>
          <div className="min-h-0 overflow-y-auto p-4 text-sm text-gray-700 dark:text-gray-200 sm:p-6">
    {error && <p role="alert" className="mt-2 text-xs text-red-600">{error}</p>}
    <fieldset disabled={disabled || busy} className="space-y-4 text-sm">
      <label className="flex gap-2"><input type="checkbox" checked={!!values.music_ducking} onChange={event => change("music_ducking", event.target.checked)} />Automatically lower music during speech</label>
      <label className="block">Music volume · {Math.round((values.music_volume || 0) * 100)}%<input type="range" min="0" max="1" step="0.01" value={values.music_volume ?? 0.07} onChange={event => change("music_volume", Number(event.target.value))} className="block w-full" /></label>
      {values.music_ducking && <label className="block">Keep {Math.round((values.duck_level || 0) * 100)}% of music volume during speech<input type="range" min="0" max="1" step="0.01" value={values.duck_level ?? 0.25} onChange={event => change("duck_level", Number(event.target.value))} className="block w-full" /></label>}
      <div className="grid grid-cols-2 gap-2">{[["music_fade_in", "Fade in (s)", 0, 30], ["music_fade_out", "Fade out (s)", 0, 30], ...(values.music_ducking ? [["duck_attack", "Lower over (s)", 0.05, 5], ["duck_release", "Restore over (s)", 0.05, 5]] : [])].map(([key, label, min, max]) => <label key={key}>{label}<input type="number" min={min} max={max} step="0.05" value={values[key] ?? 0} onChange={event => change(key, Number(event.target.value))} className="mt-1 w-full rounded-lg border border-gray-200 bg-white px-2 py-1.5 dark:border-gray-600 dark:bg-gray-800" /></label>)}</div>
      <button type="button" onClick={save} className="rounded-lg bg-blue-600 px-3 py-2 font-semibold text-white">{busy ? "Saving…" : "Save music settings"}</button>
    </fieldset>
          </div>
        </DialogPanel>
      </div>
    </Dialog>
  </section>;
}
