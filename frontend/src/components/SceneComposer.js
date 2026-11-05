import { useState } from "react";
import { RiCheckLine, RiCloseLine, RiFilmLine, RiUpload2Line, RiVolumeUpLine } from "react-icons/ri";
import { useObjectUrl } from "../hooks/useObjectUrl";
import { isVideo } from "../utils/media";

export function SceneCreationChoices({ label, value, onChange, choices }) {
  return <div role="group" aria-label={label} className="grid grid-cols-2 gap-3">
    {choices.map(({ value: option, label: title, detail, icon: Icon }) => <button key={option} type="button" aria-pressed={value === option} onClick={() => onChange(option)} className={`scene-composer-choice relative flex min-w-0 flex-col items-start gap-3 rounded-2xl border p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${value === option ? "border-blue-500 bg-blue-50/70 dark:bg-blue-500/10" : "border-gray-200 bg-white hover:border-blue-300 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-gray-500"}`}>
      <span className={`flex h-9 w-9 items-center justify-center rounded-xl ${value === option ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-300"}`}><Icon aria-hidden="true" className="h-5 w-5" /></span>
      {value === option && <RiCheckLine aria-hidden="true" className="absolute right-3 top-3 h-4 w-4 text-blue-600 dark:text-blue-300" />}
      <span><span className="block text-sm font-semibold">{title}</span><span className="mt-1 block text-xs leading-relaxed text-gray-500 dark:text-gray-400">{detail}</span></span>
    </button>)}
  </div>;
}

export function SceneMediaUpload({ file, onChange, onError, disabled, inputId }) {
  const [dragging, setDragging] = useState(false);
  const choose = next => {
    if (!next || disabled) return;
    if (next.size > 100 * 1024 * 1024) { onError("Choose an image or video smaller than 100 MB."); return; }
    if (!/^(image|video)\//.test(next.type) && !/\.(png|jpe?g|webp|gif|mp4|mov|webm|avi|m4v)$/i.test(next.name)) {
      onError("Choose an image or a video file."); return;
    }
    onError(""); onChange(next);
  };
  return <div>
    <div onDragOver={event => { event.preventDefault(); if (!disabled) setDragging(true); }} onDragLeave={event => { if (!event.currentTarget.contains(event.relatedTarget)) setDragging(false); }} onDrop={event => { event.preventDefault(); setDragging(false); choose(event.dataTransfer.files[0]); }} className={`scene-media-drop rounded-2xl border border-dashed p-5 transition-colors ${dragging ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30" : "border-gray-300 bg-gray-50 dark:border-gray-600 dark:bg-gray-900/40"}`}>
      <label htmlFor={inputId} className="flex cursor-pointer flex-col items-center gap-2 text-center">
        <span className="mb-1 flex h-10 w-10 items-center justify-center rounded-xl bg-white text-blue-600 shadow-sm dark:bg-gray-800 dark:text-blue-300"><RiUpload2Line aria-hidden="true" className="h-5 w-5" /></span>
        <span className="text-sm font-semibold">{file ? "Choose a different visual" : "Drop your image or video here"}</span>
        <span className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">or browse files · Up to 100 MB</span>
        <input id={inputId} type="file" aria-label="Upload a visual" accept="image/*,video/*" disabled={disabled} onChange={event => { choose(event.target.files[0]); event.target.value = ""; }} className="mt-2 block w-full max-w-full text-xs text-gray-500 file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:font-semibold file:text-blue-700 dark:file:bg-blue-950 dark:file:text-blue-200" />
      </label>
    </div>
    {file && <div className="mt-3 flex min-w-0 items-center gap-3 rounded-xl border border-gray-200 p-3 dark:border-gray-700"><RiFilmLine aria-hidden="true" className="h-5 w-5 shrink-0 text-blue-500" /><div className="min-w-0 flex-1"><p className="truncate text-xs font-semibold">{file.name}</p><p className="mt-1 text-[11px] text-gray-500">{(file.size / 1024 / 1024).toFixed(1)} MB</p></div><button type="button" disabled={disabled} aria-label="Remove uploaded visual" onClick={() => onChange(null)} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-blue-500 dark:hover:bg-gray-700"><RiCloseLine aria-hidden="true" className="h-4 w-4" /></button></div>}
  </div>;
}

export function SceneDraftPreview({ file, text, description, count = 1, duration, manual = false, videoFormat = "LANDSCAPE" }) {
  const source = useObjectUrl(file);
  const words = text?.trim().split(/\s+/).filter(Boolean).length || 0;
  const ratio = { LANDSCAPE: "16 / 9", PORTRAIT: "9 / 16", SQUARE: "1 / 1" }[videoFormat] || "16 / 9";
  return <section aria-label="New scene preview" className="scene-composer-card overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900/40">
    <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-700"><h3 className="text-xs font-semibold">Scene draft</h3><span className="rounded-full bg-blue-50 px-2 py-1 text-[10px] font-semibold text-blue-700 dark:bg-blue-500/10 dark:text-blue-300">{count > 1 ? `${count} scenes` : "New scene"}</span></div>
    <div className="scene-preview-surface bg-gray-950 p-3">
      <div style={{ aspectRatio: source ? ratio : undefined, minHeight: source ? undefined : 96, maxWidth: source && videoFormat === "PORTRAIT" ? 124 : source && videoFormat === "SQUARE" ? 220 : undefined }} className="scene-preview-frame relative mx-auto flex w-full items-center justify-center overflow-hidden rounded-xl bg-gray-900">
        {source ? isVideo(file) ? <video key={source} src={source} controls muted playsInline preload="metadata" aria-label="Uploaded scene visual preview" className="absolute inset-0 h-full w-full object-cover" /> : <img src={source} alt="Uploaded scene visual" className="absolute inset-0 h-full w-full object-cover" /> : <div className="flex flex-col items-center gap-2 p-4 text-center text-gray-500"><RiFilmLine aria-hidden="true" className="h-7 w-7" /><p className="text-xs leading-relaxed">{manual ? "Your canvas starts here" : description?.trim() ? "Visual will be generated" : "Your next scene"}</p></div>}
      </div>
    </div>
    <div className="space-y-3 p-4"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-gray-500"><RiVolumeUpLine aria-hidden="true" className="h-3.5 w-3.5" />{manual ? "Caption text" : "Narration"}</div><p className="line-clamp-4 whitespace-pre-wrap break-words text-sm leading-relaxed text-gray-700 dark:text-gray-200">{text?.trim() || (manual ? "Add some words, or keep the focus on your visual." : "Your dialogue will appear here as you write.")}</p><p className="border-t border-gray-100 pt-3 text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">{duration ? `${duration}s duration` : !manual && words ? `About ${Math.max(1, Math.round(words / 2.5))}s of narration` : "Duration set automatically"}</p></div>
  </section>;
}
