import { useEffect, useRef, useState } from "react";
import { Dialog, DialogBackdrop, DialogPanel, DialogTitle, Description } from "@headlessui/react";
import { HiOutlineXMark } from "react-icons/hi2";
import { getSceneWaveform, updateSceneAudio, uploadVoiceover, removeVoiceover } from "../api/apiService";
import { API_HOST } from "../endpoints";
import { voiceGain } from "./audioEnvelope";

const sourceUrl = source => /^https?:\/\//i.test(source || "") ? source : `${API_HOST}${source}`;
const inputClass = "w-full rounded-lg border border-gray-200 bg-white px-2 py-1.5 dark:border-gray-600 dark:bg-gray-800";
const defaults = { trim_start: 0, trim_end: null, delay: 0, fade_in: 0, fade_out: 0, crossfade: 0, volume: 1 };

export function SceneAudio({ scene, disabled, onSaved }) {
  const [open, setOpen] = useState(false);
  const [settings, setSettings] = useState({ ...defaults, ...scene.audio_settings });
  const [wave, setWave] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [starting, setStarting] = useState(false);
  const [file, setFile] = useState(null);
  const [audition, setAudition] = useState(false);
  const [position, setPosition] = useState(0);
  const recorder = useRef(null), stream = useRef(null), mounted = useRef(true), player = useRef(null);
  const [localUrl, setLocalUrl] = useState("");
  const source = scene.voiceover || scene.file;
  const savedSettings = JSON.stringify(scene.audio_settings || {});
  const recordingAllowed = useRef(false);
  recordingAllowed.current = open && !disabled;
  const recordingTimer = useRef(null);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; clearTimeout(recordingTimer.current); recorder.current?.state === "recording" && recorder.current.stop(); stream.current?.getTracks().forEach(track => track.stop()); };
  }, []);
  useEffect(() => {
    if (!file) { setLocalUrl(""); return; }
    const url = URL.createObjectURL(file);
    setLocalUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => { setSettings({ ...defaults, ...JSON.parse(savedSettings) }); }, [savedSettings]);
  useEffect(() => {
    if (!open || !source) { setWave(null); return; }
    let current = true;
    setLoading(true); setWave(null);
    getSceneWaveform(scene.id).then(response => {
      if (!current) return;
      setLoading(false);
      if (response.ok) setWave(response.data);
      else setError(response.message || "Could not load the waveform.");
    }).catch(() => { if (current) { setLoading(false); setError("Could not load the waveform."); } });
    return () => { current = false; };
  }, [open, source, scene.id]);
  useEffect(() => { if (disabled || !open) { player.current?.pause(); setAudition(false); recorder.current?.state === "recording" && recorder.current.stop(); } }, [disabled, open]);
  const duration = wave?.duration || 0;
  const end = settings.trim_end ?? duration;
  const update = (key, value) => { player.current?.pause(); setAudition(false); setSettings(current => ({ ...current, [key]: value })); };
  const perform = async task => {
    if (busy || disabled) return;
    setBusy(true); setError(""); player.current?.pause(); setAudition(false);
    try {
      const response = await task();
      if (!mounted.current) return;
      if (response.ok) { setFile(null); onSaved(); }
      else setError(response.message || "Could not save audio. Try again.");
    } catch { if (mounted.current) setError("Could not save audio. Try again."); }
    finally { if (mounted.current) setBusy(false); }
  };
  const startRecording = async () => {
    if (disabled || busy || starting || recording) return;
    setStarting(true); setError("");
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current || !recordingAllowed.current) { media.getTracks().forEach(track => track.stop()); return; }
      stream.current = media;
      const type = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"].find(value => MediaRecorder.isTypeSupported(value));
      const recordingDevice = new MediaRecorder(media, type ? { mimeType: type } : undefined);
      recorder.current = recordingDevice;
      const chunks = [];
      recordingDevice.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      recordingDevice.onstop = () => {
        clearTimeout(recordingTimer.current);
        media.getTracks().forEach(track => track.stop());
        if (!mounted.current) return;
        setRecording(false);
        const extension = recordingDevice.mimeType.includes("mp4") ? "m4a" : recordingDevice.mimeType.includes("ogg") ? "ogg" : "webm";
        if (chunks.length) setFile(new File(chunks, `voiceover.${extension}`, { type: recordingDevice.mimeType }));
      };
      recordingDevice.onerror = () => { media.getTracks().forEach(track => track.stop()); if (mounted.current) { setRecording(false); setError("Recording failed. Try again."); } };
      recordingDevice.start(); setRecording(true);
      recordingTimer.current = setTimeout(() => { if (recordingDevice.state === "recording") recordingDevice.stop(); }, 900000);
    } catch { stream.current?.getTracks().forEach(track => track.stop()); if (mounted.current) setError("Microphone access failed. Allow microphone access or upload an audio file."); }
    finally { if (mounted.current) setStarting(false); }
  };
  const previewTrim = async () => {
    const audio = player.current;
    if (!audio) return;
    if (audition) { audio.pause(); setAudition(false); return; }
    audio.currentTime = settings.trim_start;
    audio.volume = voiceGain(0, { duration: end - settings.trim_start, fade_in: settings.fade_in, fade_out: settings.fade_out, volume: settings.volume });
    try { await audio.play(); setAudition(true); } catch { setError("Could not play this audio. Try again."); }
  };
  return <section className="mt-4 border-t border-gray-100 pt-4 text-sm dark:border-gray-700">
    <button type="button" disabled={disabled} aria-haspopup="dialog" onClick={() => setOpen(true)} className="font-semibold text-blue-600 disabled:opacity-40 dark:text-blue-400">Edit audio · Voiceover, trim & fades</button>
    <Dialog open={open} onClose={() => setOpen(false)} className="relative z-50">
      <DialogBackdrop className="fixed inset-0 bg-gray-950/70 backdrop-blur-sm" />
      <div className="fixed inset-0 flex items-center justify-center p-3 sm:p-6">
        <DialogPanel className="flex max-h-[calc(100dvh-1.5rem)] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl dark:border-gray-700 dark:bg-gray-900 sm:max-h-[calc(100dvh-3rem)]">
          <header className="flex shrink-0 items-start justify-between gap-4 border-b border-gray-100 px-4 py-4 dark:border-gray-800 sm:px-6">
            <div><DialogTitle className="text-lg font-semibold text-gray-900 dark:text-white">Scene {scene.position} audio</DialogTitle><Description className="mt-1 text-sm text-gray-500 dark:text-gray-400">Record or upload a voiceover, trim it, and smooth the transitions.</Description></div>
            <button type="button" data-autofocus aria-label="Close audio editor" onClick={() => setOpen(false)} className="rounded-full p-2 text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:hover:bg-gray-800"><HiOutlineXMark className="h-5 w-5" /></button>
          </header>
          <div className="min-h-0 space-y-4 overflow-y-auto p-4 text-sm text-gray-700 dark:text-gray-200 sm:p-6">
      {error && <p role="alert" className="text-red-600 dark:text-red-400">{error}</p>}
      <fieldset disabled={disabled || busy || recording || starting} className="space-y-3 disabled:opacity-60">
        <label className="block">Upload voiceover<input type="file" accept="audio/*,.webm" onChange={event => { setError(""); const next = event.target.files[0]; if (next?.size > 50 * 1024 * 1024) { setError("Audio must be smaller than 50 MB."); return; } setFile(next || null); }} className="mt-1 block w-full text-xs" /></label>
        {file && <div className="space-y-2"><p className="truncate text-xs">{file.name}</p><audio src={localUrl} controls className="h-10 w-full" /><div className="flex gap-3"><button type="button" onClick={() => perform(() => { const data = new FormData(); data.append("file", file); return uploadVoiceover(scene.id, data); })} className="font-semibold text-blue-600">Use this voiceover</button><button type="button" onClick={() => setFile(null)}>Discard take</button></div></div>}
        {scene.voiceover && <button type="button" onClick={() => perform(() => removeVoiceover(scene.id))} className="text-blue-600">Restore generated narration</button>}
      </fieldset>
      {navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined" ? <button type="button" disabled={disabled || busy || starting} onClick={() => recording ? recorder.current?.stop() : startRecording()} className="rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-600">{recording ? "Stop recording" : starting ? "Opening microphone…" : file ? "Record another take" : "Record voiceover"}</button> : <p className="text-xs text-gray-500">Recording requires a supported browser on HTTPS or localhost. You can upload a voiceover.</p>}
      {recording && <p role="status" className="text-red-600">Recording… Press Stop when finished.</p>}
      {loading && <p role="status">Loading waveform…</p>}
      {source && wave && <fieldset disabled={disabled || busy || recording || starting} className="space-y-3">
        <p className="text-xs text-gray-500">{scene.voiceover ? "Uploaded voiceover" : "Generated narration"} · {duration.toFixed(2)}s</p>
        <svg viewBox="0 0 600 90" role="img" aria-label="Audio waveform; shaded areas are trimmed out" className="h-24 w-full rounded-lg bg-gray-100 dark:bg-gray-900">
          {wave.peaks.map((peak, index) => <line key={index} x1={index * 600 / wave.peaks.length} x2={index * 600 / wave.peaks.length} y1={45 - peak * 40} y2={45 + peak * 40} stroke="currentColor" className="text-blue-500" />)}
          <rect width={settings.trim_start / duration * 600} height="90" fill="black" opacity="0.35" /><rect x={end / duration * 600} width={Math.max(0, (duration - end) / duration * 600)} height="90" fill="black" opacity="0.35" />
          <line x1={position / duration * 600} x2={position / duration * 600} y1="0" y2="90" stroke="#f59e0b" strokeWidth="2" />
        </svg>
        <label className="block text-xs">Trim start · {settings.trim_start.toFixed(2)}s<input aria-label="Trim start" type="range" min="0" max={Math.max(0, end - 0.01)} step="0.01" value={settings.trim_start} onChange={event => update("trim_start", Number(event.target.value))} className="block w-full" /></label>
        <label className="block text-xs">Trim end · {end.toFixed(2)}s<input aria-label="Trim end" type="range" min={settings.trim_start + 0.01} max={duration} step="0.01" value={end} onChange={event => update("trim_end", Number(event.target.value))} className="block w-full" /></label>
        <div className="grid grid-cols-2 gap-3">{[["delay", "Start delay (s)", 60], ["fade_in", "Fade in (s)", 30], ["fade_out", "Fade out (s)", 30], ["crossfade", "Crossfade to next (s)", 10]].map(([key, label, max]) => <label key={key} className="text-xs">{label}<input type="number" min="0" max={max} step="0.1" value={settings[key]} onChange={event => update(key, Number(event.target.value))} className={inputClass} /></label>)}</div>
        <label className="block text-xs">Voice volume · {Math.round(settings.volume * 100)}%<input type="range" min="0" max="1" step="0.01" value={settings.volume} onChange={event => update("volume", Number(event.target.value))} className="block w-full" /></label>
        <p className="text-xs text-gray-500">Crossfades apply when adjacent voice clips meet. The next voice starts slightly early; pauses remain silent. Start delay is heard in the full video preview.</p>
        <audio ref={player} src={sourceUrl(source)} preload="metadata" onTimeUpdate={event => { const audio = event.currentTarget; setPosition(audio.currentTime); audio.volume = voiceGain(audio.currentTime - settings.trim_start, { duration: end - settings.trim_start, fade_in: Math.min(settings.fade_in, (end - settings.trim_start) / 2), fade_out: Math.min(settings.fade_out, (end - settings.trim_start) / 2), volume: settings.volume }); if (audio.currentTime >= end) { audio.pause(); setAudition(false); } }} onEnded={() => setAudition(false)} onError={() => setError("Could not play this audio.")} />
        <div className="flex flex-wrap gap-3"><button type="button" onClick={previewTrim} className="font-semibold text-blue-600">{audition ? "Pause" : "Listen to trim"}</button><button type="button" onClick={() => perform(() => updateSceneAudio(scene.id, settings))} className="rounded-lg bg-blue-600 px-3 py-2 font-semibold text-white">Save audio edits</button><button type="button" onClick={() => setSettings({ ...defaults })}>Reset controls</button></div>
      </fieldset>}
      {busy && <p role="status">Saving audio…</p>}
          </div>
        </DialogPanel>
      </div>
    </Dialog>
  </section>;
}
