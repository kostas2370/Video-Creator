import { useEffect, useRef, useState } from "react";
import { HiOutlineArrowUpTray, HiOutlineMicrophone, HiOutlinePlay, HiOutlinePause, HiOutlineSpeakerWave } from "react-icons/hi2";
import { toast } from "react-toastify";
import { EditorDialog, editorButton, editorInput } from "./ui/EditorDialog";
import { getSceneWaveform, updateSceneAudio, uploadVoiceover, removeVoiceover } from "../api/apiService";
import { API_HOST } from "../endpoints";
import { voiceGain } from "./audioEnvelope";
import { audioDefaults, crossfadeReason } from "./audioSettings";
import { useVoiceRecording } from "./useVoiceRecording";
import { AudioFadePresets } from "./AudioFadePresets";

const mediaUrl = source => /^https?:\/\//i.test(source || "") ? source : `${API_HOST}${source}`;
const clock = seconds => `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;
const quietButton = "rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-40 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700";

export function SceneAudio({ scene, index = 0, nextScene, disabled, onSaved }) {
  const [open, setOpen] = useState(false);
  return <>
    <button type="button" disabled={disabled} aria-haspopup="dialog" aria-label={`Edit audio for scene ${index + 1}`} onClick={() => setOpen(true)} className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-40 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"><HiOutlineSpeakerWave aria-hidden="true" className="h-4 w-4" />Audio</button>
    {open && <AudioEditor scene={scene} index={index} nextScene={nextScene} disabled={disabled} onSaved={onSaved} onClose={() => setOpen(false)} />}
  </>;
}

function AudioEditor({ scene, index, nextScene, disabled, onSaved, onClose }) {
  const [settings, setSettings] = useState({ ...audioDefaults, ...scene.audio_settings });
  const [baseline, setBaseline] = useState({ ...audioDefaults, ...scene.audio_settings });
  const [wave, setWave] = useState(null), [loading, setLoading] = useState(false);
  const [error, setError] = useState(""), [busy, setBusy] = useState(false);
  const [file, setFile] = useState(null), [localUrl, setLocalUrl] = useState("");
  const [restored, setRestored] = useState(false), [revision, setRevision] = useState(0);
  const [playing, setPlaying] = useState(false), [position, setPosition] = useState(0);
  const player = useRef(null), picker = useRef(null), uploaded = useRef(null), mounted = useRef(true);
  const source = restored ? scene.file : scene.voiceover || scene.file;
  const duration = wave?.duration || 0;
  const end = Math.min(settings.trim_end ?? duration, duration);
  const recording = useVoiceRecording(take => selectFile(take), setError, disabled);
  const locked = disabled || busy || recording.recording || recording.starting;
  const changed = !!file || JSON.stringify(settings) !== JSON.stringify(baseline);
  const unavailable = crossfadeReason(scene, nextScene, duration, settings);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; player.current?.pause(); };
  }, []);
  useEffect(() => { if (disabled) { recording.stop(); player.current?.pause(); } }, [disabled]);
  useEffect(() => {
    if (!file) { setLocalUrl(""); return; }
    const url = URL.createObjectURL(file); setLocalUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    if (!file && !source) { setWave(null); return; }
    let current = true;
    setLoading(true); setWave(null);
    const load = async () => {
      if (!file) {
        const response = await getSceneWaveform(scene.id);
        if (!response.ok) throw new Error(response.message || "Could not load the waveform.");
        return response.data;
      }
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      const context = new AudioContext();
      try {
        const buffer = await context.decodeAudioData(await file.arrayBuffer());
        if (buffer.duration > 900) throw new Error("Choose audio up to 15 minutes long.");
        const count = Math.min(600, buffer.length), peaks = [];
        for (let bin = 0; bin < count; bin++) {
          let peak = 0;
          const first = Math.floor(bin * buffer.length / count), last = Math.floor((bin + 1) * buffer.length / count);
          for (let channel = 0; channel < buffer.numberOfChannels; channel++) {
            const data = buffer.getChannelData(channel);
            for (let sample = first; sample < last; sample++) peak = Math.max(peak, Math.abs(data[sample]));
          }
          peaks.push(peak);
        }
        return { duration: buffer.duration, peaks };
      } finally { await context.close(); }
    };
    load().then(data => { if (current) setWave(data); }).catch(reason => { if (current) setError(reason.message || "Could not read this audio. Choose another file."); }).finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [source, file, scene.id, revision]);
  useEffect(() => {
    if (!playing) return;
    let frame;
    const tick = () => {
      const audio = player.current;
      if (!audio) return;
      setPosition(audio.currentTime);
      audio.volume = voiceGain(audio.currentTime - settings.trim_start, { duration: end - settings.trim_start, fade_in: Math.min(settings.fade_in, (end - settings.trim_start) / 2), fade_out: Math.min(settings.fade_out, (end - settings.trim_start) / 2), volume: settings.volume });
      if (audio.currentTime >= end) { audio.pause(); return; }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, settings, end]);
  const change = (key, value) => { player.current?.pause(); setError(""); setSettings(current => ({ ...current, [key]: value })); };
  const selectFile = next => {
    if (next && next.size > 50 * 1024 * 1024) { setError("Choose audio smaller than 50 MB."); return; }
    player.current?.pause(); setError(""); setFile(next); uploaded.current = null; setPosition(0);
    setSettings({ ...audioDefaults });
  };
  const preview = async () => {
    const audio = player.current;
    if (!audio) return;
    if (playing) { audio.pause(); return; }
    try { audio.currentTime = settings.trim_start; audio.volume = settings.fade_in ? 0 : settings.volume; await audio.play(); }
    catch { setError("Could not play this audio. Try again."); }
  };
  const save = async () => {
    if (locked || !changed || loading || !wave) return;
    setBusy(true); setError(""); player.current?.pause();
    try {
      if (file && uploaded.current !== file) {
        const data = new FormData(); data.append("file", file);
        const response = await uploadVoiceover(scene.id, data);
        if (!response.ok) throw new Error(response.message || "Could not upload this voiceover.");
        uploaded.current = file; setBaseline({ ...audioDefaults });
      }
      const response = await updateSceneAudio(scene.id, { ...settings, trim_end: settings.trim_end === null ? null : Math.min(settings.trim_end, duration) });
      if (!response.ok) throw new Error(uploaded.current ? `Voiceover uploaded, but edits could not be saved. ${response.message || "Try saving again."}` : response.message || "Could not save audio edits.");
      if (mounted.current) { toast.success("Audio changes saved"); onSaved(); onClose(); }
    } catch (reason) { if (mounted.current) { setError(reason.message); if (uploaded.current) onSaved(); } }
    finally { if (mounted.current) setBusy(false); }
  };
  const restore = async () => {
    if (locked) return;
    setBusy(true); setError(""); player.current?.pause();
    try {
      const response = await removeVoiceover(scene.id);
      if (!response.ok) throw new Error(response.message || "Could not restore narration.");
      if (mounted.current) { setRestored(true); setFile(null); uploaded.current = null; setSettings({ ...audioDefaults }); setBaseline({ ...audioDefaults }); setRevision(value => value + 1); onSaved(); toast.success(scene.file ? "Generated narration restored" : "Voiceover removed"); }
    } catch (reason) { if (mounted.current) setError(reason.message); }
    finally { if (mounted.current) setBusy(false); }
  };
  return <EditorDialog open onClose={onClose} title="Scene audio" description={`Scene ${index + 1} · Voiceover, timing and transitions.`} busy={busy} maxWidth="max-w-2xl" footer={<div className="flex flex-wrap items-center justify-between gap-3"><p role="status" className="text-xs text-gray-500 dark:text-gray-400">{busy ? "Saving audio…" : changed ? "Unsaved changes" : !source ? "Add a voiceover to begin" : "Audio is saved"}</p><div className="flex gap-2"><button type="button" disabled={busy} onClick={onClose} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 dark:text-gray-300">Cancel</button><button type="button" disabled={locked || loading || !wave || !changed} onClick={save} className={editorButton}>{busy ? "Saving…" : "Save changes"}</button></div></div>}>
    <div className="space-y-5">
      {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">{error}</p>}
      <section className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/40">
        <div className="flex flex-wrap items-center justify-between gap-3"><div className="min-w-0"><p className="text-sm font-semibold text-gray-900 dark:text-white">{file ? "New voiceover" : !restored && scene.voiceover ? "Your voiceover" : scene.file ? "Generated narration" : "Voiceover"}</p><p className="mt-1 truncate text-xs text-gray-500 dark:text-gray-400">{file ? file.name : source ? "Choose a replacement or edit the voice below." : "Upload or record a voice to get started."}</p></div><div className="flex flex-wrap gap-2"><button type="button" disabled={locked} onClick={() => picker.current?.click()} className={`${quietButton} flex items-center gap-2`}><HiOutlineArrowUpTray aria-hidden="true" className="h-4 w-4" />Upload</button>{navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined" && <button type="button" disabled={disabled || busy || recording.starting} onClick={() => recording.recording ? recording.stop() : recording.start()} className={`${quietButton} flex items-center gap-2 ${recording.recording ? "border-red-300 text-red-600" : ""}`}><HiOutlineMicrophone aria-hidden="true" className="h-4 w-4" />{recording.recording ? `Stop · ${clock(recording.seconds)}` : recording.starting ? "Opening mic…" : "Record"}</button>}</div></div>
        <input ref={picker} aria-label="Upload voiceover" type="file" accept="audio/*,.webm" className="hidden" onChange={event => { if (event.target.files[0]) selectFile(event.target.files[0]); event.target.value = ""; }} />
        {file && !uploaded.current && <button type="button" disabled={locked} onClick={() => { setFile(null); uploaded.current = null; setSettings({ ...baseline }); }} className="mt-3 text-xs font-medium text-gray-500 underline">Discard replacement</button>}
        {recording.recording && <p role="status" className="mt-3 text-xs font-medium text-red-600">Recording your microphone. Stop to listen before saving.</p>}
        {!navigator.mediaDevices?.getUserMedia && <p className="mt-3 text-xs text-gray-500">Microphone recording is available on HTTPS or localhost.</p>}
      </section>
      {loading && <p role="status" className="py-6 text-center text-sm text-gray-500">Preparing waveform…</p>}
      {wave && <fieldset disabled={locked} className="space-y-4">
        <div className="flex items-center justify-between gap-3"><div><p className="text-sm font-semibold text-gray-900 dark:text-white">Trim voice</p><p className="text-xs text-gray-500">{Math.max(0, end - settings.trim_start).toFixed(2)}s selected · {duration.toFixed(2)}s total</p></div><button type="button" onClick={preview} aria-label={playing ? "Pause edited voice" : "Play edited voice"} className={`${quietButton} flex items-center gap-2`}>{playing ? <HiOutlinePause aria-hidden="true" /> : <HiOutlinePlay aria-hidden="true" />}{playing ? "Pause" : "Preview"}</button></div>
        <svg viewBox="0 0 600 90" role="img" aria-label="Voice waveform; shaded areas are trimmed out" className="h-24 w-full rounded-xl bg-blue-50 dark:bg-gray-900"><line x1="0" x2="600" y1="45" y2="45" stroke="#93c5fd" />{wave.peaks.map((peak, index) => <line key={index} x1={index * 600 / wave.peaks.length} x2={index * 600 / wave.peaks.length} y1={45 - peak * 40} y2={45 + peak * 40} stroke="#3b82f6" />)}<rect width={settings.trim_start / duration * 600} height="90" fill="#64748b" opacity="0.25" /><rect x={end / duration * 600} width={Math.max(0, (duration - end) / duration * 600)} height="90" fill="#64748b" opacity="0.25" /><line x1={position / duration * 600} x2={position / duration * 600} y1="0" y2="90" stroke="#f59e0b" strokeWidth="2" /></svg>
        <div className="grid gap-3 sm:grid-cols-2"><label className="text-xs font-medium text-gray-600 dark:text-gray-300">Start · {settings.trim_start.toFixed(2)}s<input aria-label="Trim start" type="range" min="0" max={Math.max(0, end - 0.01)} step="0.01" value={settings.trim_start} onChange={event => change("trim_start", Number(event.target.value))} className="mt-2 block w-full accent-blue-600" /></label><label className="text-xs font-medium text-gray-600 dark:text-gray-300">End · {end.toFixed(2)}s<input aria-label="Trim end" type="range" min={settings.trim_start + 0.01} max={duration} step="0.01" value={end} onChange={event => change("trim_end", Number(event.target.value))} className="mt-2 block w-full accent-blue-600" /></label></div>
        <label className="block text-sm font-semibold text-gray-900 dark:text-white">Voice volume <span className="float-right font-normal text-gray-500">{Math.round(settings.volume * 100)}%</span><input type="range" min="0" max="1" step="0.01" value={settings.volume} onChange={event => change("volume", Number(event.target.value))} className="mt-2 block w-full accent-blue-600" /></label>
        <AudioFadePresets incoming={settings.fade_in} outgoing={settings.fade_out} disabled={locked} onChange={value => { change("fade_in", value); change("fade_out", value); }} />
        <details className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"><summary className="cursor-pointer text-sm font-semibold text-gray-700 dark:text-gray-200">Advanced · timing and transitions</summary><div className="mt-4 grid grid-cols-2 gap-3">{[["delay", "Start delay (s)", 60], ["fade_in", "Fade in (s)", 30], ["fade_out", "Fade out (s)", 30], ["crossfade", "Crossfade to next (s)", 10]].map(([key, label, max]) => <label key={key} className="text-xs text-gray-600 dark:text-gray-300">{label}<input type="number" disabled={key === "crossfade" && !!unavailable} min="0" max={max} step="0.1" value={settings[key]} onChange={event => change(key, Number(event.target.value))} className={`${editorInput} mt-1 disabled:opacity-40`} /></label>)}</div><p className="mt-3 text-xs text-gray-500 dark:text-gray-400">{unavailable ? `Crossfade unavailable: ${unavailable}` : "Crossfade overlaps the next voice without shifting the visuals."} Start delays are heard in the full video preview.</p><div className="mt-4 flex flex-wrap gap-4"><button type="button" onClick={() => { player.current?.pause(); setSettings({ ...audioDefaults }); }} className="text-xs font-medium text-blue-600">Reset edits</button>{scene.voiceover && !restored && <button type="button" onClick={restore} className="text-xs font-medium text-gray-500 underline">{scene.file ? "Restore generated narration" : "Remove voiceover"}</button>}</div></details>
      </fieldset>}
      <audio ref={player} src={file ? localUrl || undefined : source ? mediaUrl(source) : undefined} preload="metadata" onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => setPlaying(false)} onError={() => setError("Could not play this audio. Choose another file or try again.")} />
      {wave && <p className="text-xs text-gray-500 dark:text-gray-400">Preview plays your trim, fades and volume. Save, then use the full video preview to hear music and transitions together.</p>}
    </div>
  </EditorDialog>;
}
