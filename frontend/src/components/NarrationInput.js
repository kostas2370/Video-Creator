import React, { useState } from "react";
import { ScriptInput } from "./ScriptInput";

export function NarrationInput({ value, onChange, disabled, mode = "text", onModeChange, file, onFileChange, preview, error, loading }) {
  const [uploadError, setUploadError] = useState("");
  const chooseAudio = event => {
    const next = event.target.files?.[0];
    event.target.value = "";
    setUploadError("");
    if (!next) return;
    if (!next.name.toLowerCase().endsWith(".mp3") || next.size > 25 * 1024 * 1024 || !next.size) {
      setUploadError("Choose a spoken MP3 up to 25 MB and 15 minutes long.");
      return;
    }
    onFileChange(next);
  };
  return <div className="space-y-4">
    <div role="group" aria-label="Narration source" className="flex gap-2">
      {[['text', 'Text'], ['audio', 'MP3']].map(([key, label]) => <button key={key} type="button" aria-pressed={mode === key} disabled={disabled} onClick={() => onModeChange?.(key)} className={mode === key ? "studio-primary-button" : "studio-secondary-button"}>{label}</button>)}
    </div>
    {mode === "text" ? <ScriptInput value={value} onChange={onChange} disabled={disabled} /> : <section aria-labelledby="audio-source-heading" className="studio-panel space-y-4 p-5 sm:p-7">
      <h2 id="audio-source-heading" className="text-xl font-semibold">Start with your MP3</h2>
      <p className="text-sm leading-relaxed text-gray-500 dark:text-gray-400">Upload spoken narration. We’ll transcribe it, plan matching visuals, and split the original recording into a separate audio clip for every scene. No new narration is generated.</p>
      <label htmlFor="narration-mp3" className="block text-sm font-semibold">Your MP3</label>
      <input id="narration-mp3" type="file" accept=".mp3,audio/mpeg" disabled={disabled} onChange={chooseAudio} className="block w-full text-sm" />
      <p className="text-xs text-gray-500 dark:text-gray-400">MP3 · Up to 25 MB and 15 minutes · Speech transcription uses your configured provider.</p>
      {loading && <p role="status" className="text-sm">Saving your MP3 draft…</p>}
      {(uploadError || error) && <p role="alert" className="text-sm text-red-600 dark:text-red-300">{uploadError || error}</p>}
      {file && <div className="space-y-3"><p className="break-all text-sm font-medium">{file.name}</p>{preview && <audio controls preload="metadata" src={preview} className="w-full" aria-label="Original MP3 preview" />}<button type="button" className="studio-text-link" disabled={disabled} onClick={() => { onFileChange(null); setUploadError(""); }}>Remove MP3</button></div>}
    </section>}
  </div>;
}
