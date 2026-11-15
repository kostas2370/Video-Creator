import { useEffect, useRef, useState } from "react";
import { previewVoice } from "../api/apiService";
import { useObjectUrl } from "../hooks/useObjectUrl";

function Preview({ voice, disabled }) {
  const [audio, setAudio] = useState(null);
  const [opened, setOpened] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const current = useRef(true);
  const player = useRef(null);
  const blobUrl = useObjectUrl(audio);
  const src = voice.sample || blobUrl;
  useEffect(() => {
    current.current = true;
    return () => { current.current = false; };
  }, []);
  const listen = async () => {
    if (loading) return;
    setError("");
    if (src) {
      if (opened) player.current?.play()?.catch(() => setError("Press play to listen to this voice."));
      setOpened(true);
      return;
    }
    setLoading(true);
    try {
      const result = await previewVoice(voice.id);
      if (!current.current) return;
      if (result.ok) { setAudio(result.data); setOpened(true); }
      else setError(result.message || "Could not load this preview. Try again.");
    } catch {
      if (current.current) setError("Could not load this preview. Try again.");
    } finally {
      if (current.current) setLoading(false);
    }
  };
  return <div className="mt-3 text-sm">
    <button type="button" disabled={disabled || loading} onClick={listen} aria-label={`Listen to ${voice.name}`} className="rounded-lg border border-gray-300 px-3 py-2 font-medium hover:bg-gray-100 disabled:opacity-50 dark:border-gray-600 dark:hover:bg-gray-700">{loading ? "Loading preview…" : "▶ Listen"}</button>
    {!voice.sample && !opened && <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">Generates a short sample using your voice provider.</span>}
    {opened && src && !disabled && <audio ref={player} key={src} src={src} controls autoPlay data-voice-preview aria-label={`Preview of ${voice.name}`} className="mt-3 h-10 w-full" onError={() => setError("This preview could not be played. Try again later.")} onPlay={event => document.querySelectorAll("audio[data-voice-preview]").forEach(other => { if (other !== event.currentTarget) other.pause(); })} />}
    {error && <p role="alert" className="mt-2 text-xs text-red-600 dark:text-red-400">{error}</p>}
  </div>;
}

export function VoicePreview({ voice, disabled = false }) {
  return voice ? <Preview key={voice.id} voice={voice} disabled={disabled} /> : null;
}
