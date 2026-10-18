import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { HiOutlineMicrophone, HiOutlineTrash, HiOutlinePlay } from "react-icons/hi2";
import { cloneVoice, deleteVoice, getVoices, previewVoice, refreshVoice } from "../api/apiService";
import { useVoiceRecording } from "../components/useVoiceRecording";
import { useObjectUrl } from "../hooks/useObjectUrl";

const button = "rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50";
const secondary = "rounded-xl border border-gray-300 px-4 py-2.5 text-sm font-medium hover:bg-gray-100 disabled:opacity-50 dark:border-gray-600 dark:hover:bg-gray-700";

function VoiceCard({ voice, busy, onAction }) {
  const [preview, setPreview] = useState(null);
  const url = useObjectUrl(preview);
  const listen = () => onAction(async () => {
    const result = await previewVoice(voice.id);
    if (result.ok) setPreview(result.data);
    return result;
  });
  const remove = () => {
    if (window.confirm(`Delete “${voice.name}” from this app and ElevenLabs? Existing audio will stay in your videos. This cannot be undone.`)) {
      onAction(() => deleteVoice(voice.id), true);
    }
  };
  return <article className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
    <div className="flex items-start justify-between gap-3">
      <div><h2 className="font-semibold">{voice.name}</h2><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Private · {voice.clone_key_source === "service" ? "Service account" : "Your ElevenLabs account"}</p></div>
      <HiOutlineMicrophone aria-hidden="true" className="h-6 w-6 text-blue-500" />
    </div>
    <div className="mt-5 flex flex-wrap gap-2">
      <button type="button" disabled={busy} className={`${secondary} flex items-center gap-2`} onClick={listen}><HiOutlinePlay aria-hidden="true" />Preview voice</button>
      <button type="button" disabled={busy} className={`${secondary} flex items-center gap-2`} onClick={remove}><HiOutlineTrash aria-hidden="true" />Delete</button>
    </div>
    {url && <audio key={url} src={url} controls autoPlay className="mt-4 w-full" aria-label={`Preview of ${voice.name}`} />}
  </article>;
}

export function Voices() {
  const [voices, setVoices] = useState([]);
  const [name, setName] = useState("");
  const [sample, setSample] = useState(null);
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pendingVoice, setPendingVoice] = useState(null);
  const [reload, setReload] = useState(0);
  const url = useObjectUrl(sample);
  const recorder = useVoiceRecording(setSample, setError, busy || loading || voices.length >= 3, 120);
  const chooseSample = event => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > 20 * 1024 * 1024) {
      setError("Audio must be smaller than 20 MB.");
      return;
    }
    setSample(file);
  };
  useEffect(() => {
    let current = true;
    setLoading(true);
    getVoices(undefined, 1, { is_cloned: true, notifyError: false }).then(result => {
      if (!current) return;
      if (result.ok) setVoices(result.data.results);
      else setError(result.message);
      setLoading(false);
    });
    return () => { current = false; };
  }, [reload]);

  const run = async (operation, refresh = false) => {
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await operation();
      if (!result.ok) setError(result.message);
      else if (refresh) setReload(value => value + 1);
      return result;
    } finally { setBusy(false); }
  };
  const upload = async event => {
    event.preventDefault();
    const data = new FormData();
    data.append("name", name.trim()); data.append("file", sample); data.append("consent", String(consent));
    const result = await run(() => cloneVoice(data), true);
    if (result?.ok) {
      setName(""); setSample(null); setConsent(false);
      setPendingVoice(result.data.requires_verification ? result.data : null);
      setNotice(result.data.requires_verification ? "Voice saved. ElevenLabs requires verification before you can use it." : "Your voice is ready. Choose it in the voice selector when creating or editing a video.");
    }
  };

  const checkPending = async () => {
    const result = await run(() => refreshVoice(pendingVoice.id), true);
    if (result?.ok) {
      setPendingVoice(result.data.requires_verification ? result.data : null);
      setNotice(result.data.requires_verification ? "Verification is still required in ElevenLabs." : "Your voice is ready and now appears below.");
    }
  };

  return <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
    <header className="mb-8"><p className="mb-2 text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-400">Sound like yourself</p><h1 className="text-3xl font-bold tracking-tight">My voices</h1><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Create a private voice for your video narration. Keep up to three custom voices.</p></header>
    {error && <div role="alert" className="mb-5 rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{error}<button type="button" className="ml-3 underline" onClick={() => { setError(""); setReload(value => value + 1); }}>Reload voices</button></div>}
    {(notice || pendingVoice) && <p role="status" className="mb-5 rounded-xl bg-blue-50 p-4 text-sm text-blue-700 dark:bg-blue-950 dark:text-blue-300">{notice || "Complete verification in ElevenLabs, then check again."}{pendingVoice && <button type="button" disabled={busy || recorder.recording || recorder.starting} onClick={checkPending} className="ml-3 underline disabled:opacity-50">Check verification</button>}</p>}
    <form onSubmit={upload} className="mb-8 rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h2 className="text-lg font-semibold">Add your voice</h2>
      <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Use 10 seconds to 2 minutes of clear speech with no music or other speakers. Aim for 1–2 minutes for better results. Audio is sent to ElevenLabs to create your voice; this app does not keep the recording. Your active <Link to="/api-keys/" className="text-blue-600 underline dark:text-blue-400">ElevenLabs account</Link> needs a plan that supports voice cloning and an available voice slot.</p>
      <fieldset disabled={busy || loading || voices.length >= 3} className="mt-5 space-y-5 disabled:opacity-60">
        <div><label htmlFor="voice-name" className="mb-2 block text-sm font-medium">Voice name</label><input id="voice-name" required maxLength={80} value={name} onChange={event => setName(event.target.value)} placeholder="My narration voice" className="w-full rounded-xl border border-gray-300 bg-transparent px-3 py-2.5 dark:border-gray-600" /></div>
        <div><label htmlFor="voice-sample" className="mb-2 block text-sm font-medium">Voice sample · up to 20 MB</label><input id="voice-sample" type="file" accept="audio/*,.m4a,.webm" disabled={recorder.recording || recorder.starting} onChange={chooseSample} className="block w-full text-sm" /></div>
        <div className="flex flex-wrap items-center gap-3"><button type="button" disabled={recorder.starting} onClick={recorder.recording ? recorder.stop : recorder.start} className={secondary}>{recorder.starting ? "Opening microphone…" : recorder.recording ? `Stop recording · ${recorder.seconds}s` : "Record a sample"}</button><span className="text-xs text-gray-500 dark:text-gray-400">Recording stops after 2 minutes.</span></div>
        {sample && <div><p className="mb-2 truncate text-sm">{sample.name}</p>{url && <audio src={url} controls className="w-full" aria-label="Your uploaded voice sample" />}</div>}
        <label className="flex items-start gap-3 text-sm"><input type="checkbox" required checked={consent} onChange={event => setConsent(event.target.checked)} className="mt-1" /><span>I confirm this is my own voice and consent to sending this recording to ElevenLabs to create a synthetic voice for my narration.</span></label>
        <button type="submit" disabled={!name.trim() || !sample || !consent || recorder.recording || recorder.starting} className={button}>Create my voice</button>
      </fieldset>
      {busy && <p role="status" className="mt-4 text-sm text-gray-500">Working with ElevenLabs… This can take a minute.</p>}
      {!loading && voices.length >= 3 && <p className="mt-4 text-sm">You have three custom voices. Delete one to make room for another.</p>}
    </form>
    {loading ? <p role="status">Loading your voices…</p> : voices.length ? <div className="grid gap-5 sm:grid-cols-2">{voices.map(voice => <VoiceCard key={voice.id} voice={voice} busy={busy || recorder.recording || recorder.starting} onAction={run} />)}</div> : <p className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">Your usable custom voices will appear here. Only you can access them.</p>}
    <p className="mt-6 text-xs text-gray-500 dark:text-gray-400">Creating a voice and generating previews may use your provider plan’s limits. Voices remain tied to the account and key used to create them. Deleting a voice removes it from ElevenLabs and from future voice selections; existing generated audio stays in your videos.</p>
  </main>;
}
