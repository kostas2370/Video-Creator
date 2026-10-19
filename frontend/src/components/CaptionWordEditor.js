import { useState } from "react";
import { HiOutlinePlus, HiOutlineTrash } from "react-icons/hi2";
import { insertCaptionWord } from "../utils/captions";
import { editorInput } from "./ui/EditorDialog";

const PAGE_SIZE = 50;

export function CaptionWordEditor({ words, onChange, duration, time, disabled, onSeek, onError, emptyMessage }) {
  const [page, setPage] = useState(0);
  const currentPage = Math.min(page, Math.max(0, Math.ceil(words.length / PAGE_SIZE) - 1));
  const edit = (index, key, value) => onChange(words.map((word, at) => at === index ? { ...word, [key]: value } : word));
  const add = () => {
    const inserted = insertCaptionWord(words, time, duration);
    if (!inserted) { onError("There isn’t room for a word here. Adjust the neighboring times or jump to a gap first."); return; }
    onChange(inserted.words); setPage(Math.floor(inserted.index / PAGE_SIZE)); onError("");
  };
  return <div className="min-w-0">
    <div className="mb-4 flex items-center justify-between gap-3"><h3 className="font-semibold">Words & timing</h3><button type="button" disabled={disabled || words.length >= 10000} onClick={add} className="inline-flex items-center gap-1 text-sm font-semibold text-blue-600 disabled:opacity-40"><HiOutlinePlus aria-hidden="true" />Add word</button></div>
    <fieldset disabled={disabled}>
      <div className="mb-2 grid grid-cols-[28px_minmax(0,1fr)_70px_70px_26px] gap-2 text-xs text-gray-500"><span>#</span><span>Word</span><span>Start (s)</span><span>End (s)</span><span /></div>
      {words.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE).map((word, at) => {
        const index = currentPage * PAGE_SIZE + at;
        return <div key={index} className="mb-2 grid grid-cols-[28px_minmax(0,1fr)_70px_70px_26px] items-center gap-2">
          <button type="button" onClick={() => onSeek(word.start)} aria-label={`Jump to word ${index + 1}`} className={`text-xs tabular-nums ${time >= word.start && time < word.end ? "font-bold text-blue-600" : "text-gray-400"}`}>{index + 1}</button>
          <input aria-label={`Word ${index + 1}`} maxLength={40} value={word.text} onChange={event => edit(index, "text", event.target.value)} className={`${editorInput} min-w-0 !px-2`} />
          {["start", "end"].map(key => <input key={key} aria-label={`${key === "start" ? "Start" : "End"} of word ${index + 1}`} type="number" min={0} max={duration} step="0.001" value={Number.isFinite(word[key]) ? word[key] : ""} onChange={event => edit(index, key, event.target.value === "" ? NaN : Number(event.target.value))} className={`${editorInput} min-w-0 !px-2 !text-xs`} />)}
          <button type="button" aria-label={`Remove word ${index + 1}`} onClick={() => { onChange(words.filter((_, at) => at !== index)); setPage(currentPage); }} className="text-gray-400 hover:text-red-500"><HiOutlineTrash className="h-4 w-4" /></button>
        </div>;
      })}
      {!words.length && <p className="py-4 text-sm text-gray-500">{emptyMessage}</p>}
    </fieldset>
    {words.length > PAGE_SIZE && <div className="mt-4 flex items-center justify-between text-sm"><button type="button" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)} className="disabled:opacity-40">Previous</button><span>{currentPage + 1} / {Math.ceil(words.length / PAGE_SIZE)}</span><button type="button" disabled={(currentPage + 1) * PAGE_SIZE >= words.length} onClick={() => setPage(currentPage + 1)} className="disabled:opacity-40">Next</button></div>}
  </div>;
}
