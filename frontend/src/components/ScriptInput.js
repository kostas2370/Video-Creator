import React, { useEffect, useRef, useState } from "react";

export function ScriptInput({ value, onChange, disabled }) {
  const [error, setError] = useState("");
  const [reading, setReading] = useState(false);
  const request = useRef(0);
  useEffect(() => () => { request.current += 1; }, []);

  const upload = async event => {
    const file = event.target.files?.[0];
    event.target.value = "";
    const current = ++request.current;
    setError("");
    setReading(false);
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".txt") || file.size > 16 * 1024) {
      setError("Choose a UTF-8 .txt file up to 16 KB and 2,000 characters.");
      return;
    }
    setReading(true);
    try {
      const text = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer()).replace(/^\uFEFF/, "");
      if (current !== request.current) return;
      if (!text.trim() || text.length > 2000 || text.includes("\0")) {
        setError("Your script must contain 1–2,000 characters of plain text. Your current script is kept.");
        return;
      }
      onChange(text);
    } catch {
      if (current === request.current) setError("Could not read this file. Save it as UTF-8 plain text and try again.");
    } finally {
      if (current === request.current) setReading(false);
    }
  };

  return <section aria-labelledby="story-heading" className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-7 dark:border-gray-700 dark:bg-gray-800">
    <h2 id="story-heading" className="text-xl font-semibold tracking-tight">Start with your script</h2>
    <p id="script-help" className="mt-2 text-sm leading-relaxed text-gray-500 dark:text-gray-400">Paste the words the narrator should say. We’ll preserve your wording, split it into scenes, and suggest matching visuals. Review the storyboard before generating images and narration.</p>
    <label htmlFor="script-file" className="mt-5 block text-sm font-semibold">Upload a text file to replace the script</label>
    <input id="script-file" type="file" accept=".txt,text/plain" onChange={upload} disabled={disabled} className="mt-2 block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:text-blue-700 dark:file:bg-blue-900 dark:file:text-blue-200" />
    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">UTF-8 .txt · Up to 2,000 characters</p>
    {reading && <p role="status" className="mt-2 text-sm">Reading your script…</p>}
    {error && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-300">{error}</p>}
    <label htmlFor="message" className="mt-5 block text-sm font-semibold">Your script</label>
    <textarea id="message" name="message" aria-describedby="script-help" rows={10} maxLength={2000} required value={value} disabled={disabled} onChange={event => { request.current += 1; setReading(false); setError(""); onChange(event.target.value); }} className="mt-2 block w-full rounded-xl border border-gray-300 bg-gray-50 p-4 text-base leading-7 dark:border-gray-600 dark:bg-gray-900 dark:text-white" placeholder="Paste your narration here…" />
    <p className="mt-2 text-right text-xs tabular-nums text-gray-500 dark:text-gray-400" aria-label="Script character count">{value.length}/2000</p>
  </section>;
}
