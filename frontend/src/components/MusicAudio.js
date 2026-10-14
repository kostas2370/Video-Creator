import { useState } from "react";
import { HiOutlineAdjustmentsHorizontal } from "react-icons/hi2";
import { toast } from "react-toastify";
import { updateMusicAudio } from "../api/apiService";
import { EditorDialog, editorButton, editorInput } from "./ui/EditorDialog";
import { AudioFadePresets } from "./AudioFadePresets";

export function MusicAudio({ video, disabled, onSaved }) {
  const [open, setOpen] = useState(false);
  if (!video?.music) return null;
  return <section aria-label="Background music settings" className="mt-5 border-t border-gray-100 pt-4 dark:border-gray-700"><h3 className="text-sm font-semibold">Background music</h3><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{Math.round((video.settings?.music_volume ?? 0.07) * 100)}% volume{video.settings?.music_ducking ? " · Auto ducking on" : ""}</p><button type="button" disabled={disabled} aria-haspopup="dialog" onClick={() => setOpen(true)} className="mt-3 flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium text-gray-600 hover:bg-blue-50 hover:text-blue-600 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-40 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"><HiOutlineAdjustmentsHorizontal aria-hidden="true" className="h-4 w-4" />Edit music</button>{open && <MusicEditor video={video} disabled={disabled} onSaved={onSaved} onClose={() => setOpen(false)} />}</section>;
}

function MusicEditor({ video, disabled, onSaved, onClose }) {
  const source = video.settings || {};
  const duration = (video.scenes || []).reduce((total, scene) => total + (scene.timing?.duration || 0), 0);
  const defaultFade = Math.min(4, duration * 0.1);
  const initial = { music_ducking: source.music_ducking ?? false, music_volume: source.music_volume ?? 0.07, music_fade_in: source.music_fade_in ?? defaultFade, music_fade_out: source.music_fade_out ?? defaultFade, duck_level: source.duck_level ?? 0.25, duck_attack: source.duck_attack ?? 0.2, duck_release: source.duck_release ?? 0.8 };
  const [baseline] = useState(initial), [values, setValues] = useState(initial);
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  const changed = JSON.stringify(values) !== JSON.stringify(baseline);
  const change = (key, value) => { setError(""); setValues(current => ({ ...current, [key]: value })); };
  const save = async () => {
    if (busy || disabled || !changed) return;
    setBusy(true); setError("");
    try {
      const response = await updateMusicAudio(video.id, values);
      if (!response.ok) throw new Error(response.message || "Could not save music settings.");
      toast.success("Music settings saved"); onSaved(); onClose();
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  };
  return <EditorDialog open onClose={onClose} title="Background music" description="Keep your voice clear and music balanced." busy={busy} maxWidth="max-w-lg" footer={<div className="flex flex-wrap items-center justify-between gap-3"><p role="status" className="text-xs text-gray-500 dark:text-gray-400">{busy ? "Saving…" : changed ? "Unsaved changes" : "Settings are saved"}</p><div className="flex gap-2"><button type="button" disabled={busy} onClick={onClose} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 dark:text-gray-300">Cancel</button><button type="button" disabled={busy || disabled || !changed} onClick={save} className={editorButton}>{busy ? "Saving…" : "Save changes"}</button></div></div>}>
    <fieldset disabled={disabled || busy} className="space-y-5">
      {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">{error}</p>}
      <label className="block text-sm font-semibold text-gray-900 dark:text-white">Music volume <span className="float-right font-normal text-gray-500">{Math.round(values.music_volume * 100)}%</span><input aria-label="Music volume" type="range" min="0" max="1" step="0.01" value={values.music_volume} onChange={event => change("music_volume", Number(event.target.value))} className="mt-3 block w-full accent-blue-600" /></label>
      <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/40"><input type="checkbox" checked={values.music_ducking} onChange={event => change("music_ducking", event.target.checked)} className="mt-1 accent-blue-600" /><span><span className="block text-sm font-semibold text-gray-900 dark:text-white">Lower music during speech</span><span className="mt-1 block text-xs leading-relaxed text-gray-500 dark:text-gray-400">Music fades down while the voice speaks and returns during silence.</span></span></label>
      <AudioFadePresets incoming={values.music_fade_in} outgoing={values.music_fade_out} disabled={busy || disabled} onChange={value => { change("music_fade_in", value); change("music_fade_out", value); }} />
      <details className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"><summary className="cursor-pointer text-sm font-semibold text-gray-700 dark:text-gray-200">Advanced · fades and ducking</summary><div className="mt-4 space-y-4">{values.music_ducking && <label className="block text-xs text-gray-600 dark:text-gray-300">Music level during speech · {Math.round(values.duck_level * 100)}%<input type="range" min="0" max="1" step="0.01" value={values.duck_level} onChange={event => change("duck_level", Number(event.target.value))} className="mt-2 block w-full accent-blue-600" /></label>}<div className="grid grid-cols-2 gap-3">{[["music_fade_in", "Fade in (s)", 0, 30], ["music_fade_out", "Fade out (s)", 0, 30], ...(values.music_ducking ? [["duck_attack", "Lower over (s)", 0.05, 5], ["duck_release", "Restore over (s)", 0.05, 5]] : [])].map(([key, label, min, max]) => <label key={key} className="text-xs text-gray-600 dark:text-gray-300">{label}<input type="number" min={min} max={max} step="0.05" value={values[key]} onChange={event => change(key, Number(event.target.value))} className={`${editorInput} mt-1`} /></label>)}</div></div></details>
      <p className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">Save, then open the video preview to hear music with your voiceover.</p>
    </fieldset>
  </EditorDialog>;
}
