import { useMemo, useState } from "react";
import { editorInput } from "./ui/EditorDialog";
import { formatTime } from "../utils/clips";

export function transcriptParagraphs(words = []) {
  const paragraphs = [];
  let current = [];
  const flush = () => {
    if (current.length) paragraphs.push({ start: current[0].start, text: current.map(word => word.text).join(" ") });
    current = [];
  };
  for (const word of words) {
    if (current.length && (current.length >= 60 || word.start - current[current.length - 1].end >= 2)) flush();
    current.push(word);
    if (current.length >= 20 && /[.!?…]["”’')]*$/u.test(word.text)) flush();
  }
  flush();
  return paragraphs;
}

export function transcriptText(paragraphs) {
  return paragraphs.map(paragraph => `[${formatTime(paragraph.start)}] ${paragraph.text}`).join("\n\n");
}

export function FullVideoTranscript({ title, words = [] }) {
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const paragraphs = useMemo(() => transcriptParagraphs(words), [words]);
  const matches = useMemo(() => paragraphs.filter(paragraph => paragraph.text.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())), [paragraphs, query]);
  const fullText = useMemo(() => transcriptText(paragraphs), [paragraphs]);
  const copy = async () => {
    setError(""); setMessage("");
    try { await navigator.clipboard.writeText(fullText); setMessage("Full video transcript copied."); }
    catch { setError("Could not copy automatically. Download the transcript or select its text to copy it."); }
  };
  const download = () => {
    const url = URL.createObjectURL(new Blob([fullText], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${(title || "video").replace(/[^\p{L}\p{N} _-]/gu, "").trim().slice(0, 80) || "video"}-transcript.txt`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <details className="mb-6 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
    <summary className="cursor-pointer text-lg font-semibold">Full video transcript</summary>
    <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">The source video's complete saved transcript, with timestamps. Edits to individual clip captions do not change this text.</p>
    {!words.length ? <p role="status" className="mt-4 text-sm text-gray-500">The full transcript will appear here when transcription finishes.</p> : <>
      <div className="my-4 flex flex-wrap items-center gap-3"><label className="w-full min-w-0 sm:w-auto sm:flex-1"><span className="sr-only">Search full video transcript</span><input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search the full transcript…" className={editorInput} /></label><button type="button" onClick={copy} className="min-h-11 text-sm font-semibold text-blue-600 dark:text-blue-300">Copy full transcript</button><button type="button" onClick={download} className="min-h-11 text-sm font-semibold text-blue-600 dark:text-blue-300">Download TXT</button></div>
      {query.trim() && <p role="status" className="mb-3 text-xs text-gray-500">{matches.length} matching passages. Copy and download always include the full transcript.</p>}
      <div role="region" aria-label="Full source video transcript" tabIndex={0} className="max-h-96 space-y-4 overflow-y-auto rounded-xl bg-gray-50 p-4 dark:bg-gray-900">{matches.map(paragraph => <p key={paragraph.start} className="break-words text-sm leading-relaxed"><span className="mr-3 font-mono text-xs text-gray-500">{formatTime(paragraph.start)}</span>{paragraph.text}</p>)}{!matches.length && <p className="text-sm text-gray-500">No matching passages. Try another search.</p>}</div>
    </>}
    {message && <p role="status" className="mt-3 text-sm text-emerald-600 dark:text-emerald-300">{message}</p>}{error && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-300">{error}</p>}
  </details>;
}
