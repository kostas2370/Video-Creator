import { useEffect, useMemo, useRef, useState } from "react";
import { CaptionWordEditor } from "./CaptionWordEditor";
import { CaptionLayer } from "./CaptionLayer";
import { FontPicker } from "./FontPicker";
import { editorButton, editorInput } from "./ui/EditorDialog";
import { captionAt, captionGroups, defaultCaptionStyle, validateCaptionWords, resolveCaptionConfig } from "../utils/captions";
import { formatTime, validateClip, wordsForClip } from "../utils/clips";
import { API_HOST } from "../endpoints";
import { saveClip } from "../api/apiService";

const mediaUrl = path => /^https?:\/\//i.test(path || "") ? path : `${API_HOST}${path}`;

export function ClipEditor({ project, clip, onSaved, onClose, initialDraft, onDraftChange, onWorkingChange }) {
  const [draft, setDraft] = useState(() => initialDraft || ({ ...clip, style: { ...defaultCaptionStyle, ...clip.style } }));
  useEffect(() => { onDraftChange?.(draft); }, [draft, onDraftChange]);
  const [time, setTime] = useState(0);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [playing, setPlaying] = useState(false);
  const [transcriptPage, setTranscriptPage] = useState(0);
  const [boundary, setBoundary] = useState("start");
  const editor = useRef(null);
  useEffect(() => { editor.current?.scrollIntoView?.({ behavior: "smooth", block: "start" }); }, [clip.id]);
  const player = useRef(null);
  const backdrop = useRef(null);
  const duration = draft.end - draft.start;
  const groups = useMemo(() => captionGroups(draft.words, draft.style.preset), [draft.words, draft.style.preset]);
  const cue = captionAt(groups, time, draft.style.preset);
  const config = resolveCaptionConfig(draft.style.preset, draft.style);
  const edit = (key, value) => setDraft(current => ({ ...current, [key]: value }));
  const editStyle = (key, value) => setDraft(current => ({ ...current, style: { ...current.style, [key]: value } }));
  const trim = (key, value) => {
    player.current?.pause();
    setDraft(current => {
      const next = { ...current, [key]: value };
      next.words = wordsForClip(project.words, next.start, next.end);
      return next;
    });
    setTime(0);
  };
  const seek = relative => {
    if (player.current && Number.isFinite(relative) && Number.isFinite(draft.start)) player.current.currentTime = draft.start + relative;
    setTime(relative);
  };
  const sync = event => {
    const video = event.currentTarget;
    if (validateClip(draft.start, draft.end, project.range_end ?? project.duration, project.range_start ?? 0)) { video.pause(); return; }
    if (video.currentTime >= draft.end) { video.pause(); video.currentTime = draft.start; }
    if (video.currentTime < draft.start) video.currentTime = draft.start;
    setTime(Math.max(0, video.currentTime - draft.start));
    if (backdrop.current && Math.abs(backdrop.current.currentTime - video.currentTime) > 0.2) backdrop.current.currentTime = video.currentTime;
  };
  const submit = async event => {
    event.preventDefault();
    const message = validateClip(draft.start, draft.end, project.range_end ?? project.duration, project.range_start ?? 0) || validateCaptionWords(draft.words, duration);
    if (message) { setError(message); return; }
    setWorking(true); onWorkingChange?.(true); setError(""); player.current?.pause();
    const { id, reason, hashtags, output, status, error: previousError, ...changes } = draft;
    try {
      const result = await saveClip(project.id, clip.id, changes);
      if (result.ok) onSaved(result.data); else setError(result.message);
    } catch { setError("Could not save this clip. Your edits are still here; please retry."); }
    finally { setWorking(false); onWorkingChange?.(false); }
  };
  const source = mediaUrl(project.preview || project.source);
  const transcriptPages = Math.ceil(project.words.length / 150);
  return <section ref={editor} aria-label="Clip editor" className="clip-panel rounded-2xl border border-blue-200 bg-white p-4 sm:p-6 dark:border-blue-900 dark:bg-gray-800">
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3"><div className="min-w-0"><p className="mb-1 text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-300">Clip studio</p><h2 className="text-xl font-bold">Edit clip</h2><p className="mt-1 max-w-md truncate text-sm text-gray-500">{clip.title}</p></div><button type="button" disabled={working} onClick={() => { player.current?.pause(); onClose(); }} className="min-h-11 text-sm text-gray-500">Close without saving</button></div>
    {error && <p role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">{error}</p>}
    <form onSubmit={submit} onInvalidCapture={() => setError("Check the highlighted fields before saving this clip.")}>
      <fieldset disabled={working} className="min-w-0">
        <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(200px,280px)_minmax(0,1fr)]">
          <div>
            <div className="relative mx-auto aspect-[9/16] w-full max-w-[340px] overflow-hidden rounded-xl bg-black">
              {draft.layout === "FIT" && <video ref={backdrop} src={source} muted playsInline aria-hidden="true" className="absolute inset-0 h-full w-full scale-110 object-cover blur-xl" />}
              <video key={`${clip.id}-${draft.start}`} ref={player} src={source} playsInline preload="metadata" onLoadedMetadata={() => seek(0)} onTimeUpdate={sync} onSeeked={sync} onPlay={() => { setPlaying(true); if (backdrop.current) { backdrop.current.currentTime = player.current.currentTime; backdrop.current.play().catch(() => {}); } }} onPause={() => { setPlaying(false); backdrop.current?.pause(); }} onError={() => setError("Could not play this preview. Try reloading the project.")} className={`absolute inset-0 h-full w-full ${draft.layout === "CROP" ? "object-cover" : "object-contain"}`} style={{ objectPosition: `${draft.crop_position}% 50%` }} />
              {draft.captions && <CaptionLayer cue={cue} style={config} size={[720, 1280]} />}
            </div>
            <div className="mt-3 flex items-center gap-3"><button type="button" disabled={!!validateClip(draft.start, draft.end, project.range_end ?? project.duration, project.range_start ?? 0)} onClick={() => playing ? player.current?.pause() : player.current?.play().catch(() => {})} className="rounded-lg bg-gray-100 px-3 py-2 text-sm dark:bg-gray-700">{playing ? "Pause" : "Play"}</button><input aria-label="Clip preview position" type="range" min={0} max={Number.isFinite(duration) && duration > 0 ? duration : 1} step="0.05" value={Number.isFinite(duration) ? Math.min(time, Math.max(0, duration)) : 0} onChange={event => seek(Number(event.target.value))} className="min-w-0 flex-1" /><span className="text-xs tabular-nums">{formatTime(time)}</span></div>
            <p className="mt-2 text-xs text-gray-500">Preview · exports use the original footage</p>
          </div>
          <div className="min-w-0 space-y-4">
            <label className="block text-sm font-medium">Clip title<input required maxLength={100} value={draft.title} onChange={event => edit("title", event.target.value)} className={`${editorInput} mt-2`} /></label>
            <div className="grid grid-cols-2 gap-3">{["start", "end"].map(key => <label key={key} className="text-sm">{key === "start" ? "Start" : "End"} (seconds)<input type="number" required min={project.range_start ?? 0} max={project.range_end ?? project.duration} step="any" value={Number.isFinite(draft[key]) ? draft[key] : ""} onChange={event => trim(key, event.target.value === "" ? NaN : Number(event.target.value))} className={`${editorInput} mt-2`} /></label>)}</div>
            <p className="text-xs text-gray-500">{Number.isFinite(duration) ? `${duration.toFixed(1)} seconds` : "Enter clip times"} · Changing the trim rebuilds captions from the original transcript.</p>
            <label className="block text-sm">Portrait layout<select value={draft.layout} onChange={event => edit("layout", event.target.value)} className={`${editorInput} mt-2`}><option value="FIT">Full picture with blurred background</option><option value="CROP">Crop to portrait</option></select></label>
            {draft.layout === "CROP" && <label className="block text-sm">Horizontal framing<input aria-label="Horizontal framing" type="range" min={0} max={100} value={draft.crop_position} onChange={event => edit("crop_position", Number(event.target.value))} className="mt-2 w-full" /><span className="flex justify-between text-xs text-gray-500"><span>Left</span><span>Right</span></span></label>}
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={draft.captions} onChange={event => edit("captions", event.target.checked)} />Show captions</label>
            {draft.captions && <div className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 [&_label]:min-w-0"><label className="text-sm">Style<select value={draft.style.preset} onChange={event => editStyle("preset", event.target.value)} className={`${editorInput} mt-2`}><option value="TIKTOK">Word highlights</option><option value="CLASSIC">Classic subtitles</option></select></label><label className="text-sm">Position<select value={draft.style.position} onChange={event => editStyle("position", event.target.value)} className={`${editorInput} mt-2`}><option value="bottom">Lower area</option><option value="middle">Center</option><option value="top">Upper area</option></select></label><FontPicker value={draft.style.font} onChange={font => editStyle("font", font)} /><label className="text-sm">Text size<input type="range" min={3} max={9} value={draft.style.size} onChange={event => editStyle("size", Number(event.target.value))} className="mt-3 w-full" /></label><label className="text-sm">Text color<input type="color" value={draft.style.color} onChange={event => editStyle("color", event.target.value)} className="mt-2 block h-9 w-full" /></label><label className="text-sm">Highlight color<input type="color" value={draft.style.highlight} onChange={event => editStyle("highlight", event.target.value)} className="mt-2 block h-9 w-full" /></label></div>}

          </div>
        </div>
        <details className="mt-6 min-w-0 border-t border-gray-200 pt-4 dark:border-gray-700"><summary className="cursor-pointer font-semibold">Choose boundaries from the transcript</summary><div className="my-3 flex gap-3 text-sm">{["start", "end"].map(value => <label key={value} className="flex items-center gap-2"><input type="radio" name="boundary" checked={boundary === value} onChange={() => setBoundary(value)} />Set {value}</label>)}</div><div className="max-h-60 overflow-y-auto rounded-xl bg-gray-50 p-3 text-sm break-words leading-8 dark:bg-gray-900">{project.words.slice(transcriptPage * 150, (transcriptPage + 1) * 150).map((word, index) => <button key={index} type="button" title={`Set ${boundary} at ${formatTime(word[boundary])}`} onClick={() => trim(boundary, word[boundary])} className={`mr-1 min-h-10 rounded px-1 hover:bg-blue-200 dark:hover:bg-blue-800 ${word.start >= draft.start && word.end <= draft.end ? "bg-blue-100 dark:bg-blue-950" : ""}`}>{word.text}</button>)}</div>{transcriptPages > 1 && <div className="mt-3 flex justify-between text-sm"><button type="button" disabled={!transcriptPage} onClick={() => setTranscriptPage(value => value - 1)}>Previous words</button><span>{transcriptPage + 1} / {transcriptPages}</span><button type="button" disabled={transcriptPage + 1 >= transcriptPages} onClick={() => setTranscriptPage(value => value + 1)}>Next words</button></div>}</details>
        {draft.captions && <details className="mt-5 border-t border-gray-200 pt-4 dark:border-gray-700"><summary className="mb-4 cursor-pointer font-semibold">Edit caption words and timing</summary><CaptionWordEditor words={draft.words} onChange={words => edit("words", words)} duration={Math.max(0, duration)} time={time} disabled={working} onSeek={seek} onError={setError} emptyMessage="No spoken words in this excerpt." /></details>}
        <div className="clip-savebar sticky bottom-0 z-10 -mx-4 mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-gray-200 bg-white/95 px-4 py-4 backdrop-blur sm:-mx-6 sm:px-6 dark:border-gray-700 dark:bg-gray-800/95"><p className="text-xs text-gray-500">{working ? "Saving your changes…" : "Save your changes before exporting."}</p><button className={editorButton} type="submit">{working ? "Saving…" : "Save clip"}</button></div>
      </fieldset>
    </form>
  </section>;
}
