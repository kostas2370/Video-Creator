import { useEffect, useRef, useState } from "react";

export function useVoiceRecording(onTake, onError, disabled = false, maxSeconds = 900) {
  const [recording, setRecording] = useState(false);
  const [starting, setStarting] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const device = useRef(null), stream = useRef(null), mounted = useRef(true), limit = useRef(null);
  const allowed = useRef(true);
  allowed.current = !disabled;
  const callbacks = useRef({ onTake, onError });
  callbacks.current = { onTake, onError };
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; clearTimeout(limit.current); if (device.current?.state === "recording") device.current.stop(); stream.current?.getTracks().forEach(track => track.stop()); };
  }, []);
  useEffect(() => {
    if (!recording) return;
    const start = performance.now();
    const timer = setInterval(() => setSeconds(Math.floor((performance.now() - start) / 1000)), 250);
    return () => clearInterval(timer);
  }, [recording]);
  const stop = () => { if (device.current?.state === "recording") device.current.stop(); };
  const start = async () => {
    if (recording || starting || !allowed.current) return;
    setStarting(true);
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current || !allowed.current) { media.getTracks().forEach(track => track.stop()); return; }
      stream.current = media;
      const type = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"].find(value => MediaRecorder.isTypeSupported(value));
      const recorder = new MediaRecorder(media, type ? { mimeType: type } : undefined);
      device.current = recorder;
      const chunks = [];
      recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      recorder.onstop = () => {
        clearTimeout(limit.current); media.getTracks().forEach(track => track.stop());
        if (!mounted.current) return;
        setRecording(false);
        const extension = recorder.mimeType.includes("mp4") ? "m4a" : recorder.mimeType.includes("ogg") ? "ogg" : "webm";
        if (chunks.length) callbacks.current.onTake(new File(chunks, `voiceover.${extension}`, { type: recorder.mimeType }));
      };
      recorder.onerror = () => { stop(); media.getTracks().forEach(track => track.stop()); if (mounted.current) { setRecording(false); callbacks.current.onError("Recording failed. Try again."); } };
      recorder.start(); setSeconds(0); setRecording(true);
      limit.current = setTimeout(stop, maxSeconds * 1000);
    } catch { stream.current?.getTracks().forEach(track => track.stop()); if (mounted.current) callbacks.current.onError("Allow microphone access, or upload an audio file."); }
    finally { if (mounted.current) setStarting(false); }
  };
  return { start, stop, recording, starting, seconds };
}
