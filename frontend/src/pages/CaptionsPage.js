import { FontPicker } from "../components/FontPicker";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { HiOutlineArrowUpTray, HiOutlineSparkles, HiOutlinePlus, HiOutlineTrash, HiOutlineArrowDownTray } from "react-icons/hi2";
import { CaptionLayer } from "../components/CaptionLayer";
import { VideoCreationMode } from "../components/VideoCreationMode";
import { editorInput, editorButton } from "../components/ui/EditorDialog";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";
import { createCaptionProject, getCaptionProject, getCaptionProjects, saveCaptionProject, transcribeCaptionProject, renderCaptionProject, downloadCaptionProject } from "../api/apiService";
import { API_HOST } from "../endpoints";
import { captionAt, captionBusy, captionGroups, defaultCaptionStyle, validateCaptionWords } from "../utils/captions";

const statusLabels = { QUEUED: "Waiting to transcribe", TRANSCRIBING: "Listening and aligning words…", READY: "Ready to edit", RENDER_QUEUED: "Waiting to export", RENDERING: "Creating your captioned video…", COMPLETED: "Export ready", FAILED: "Needs attention" };
const mediaUrl = path => /^https?:\/\//i.test(path || "") ? path : `${API_HOST}${path}`;
const PAGE_SIZE = 40;

export function Captions() {
  useAxiosPrivate();
  const { captionId } = useParams();
  const navigate = useNavigate();
  const player = useRef(null);
  const [projects, setProjects] = useState([]);
  const [projectPage, setProjectPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [project, setProject] = useState(null);
  const [words, setWords] = useState([]);
  const [style, setStyle] = useState(defaultCaptionStyle);
  const [file, setFile] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [working, setWorking] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [time, setTime] = useState(0);
  const [page, setPage] = useState(0);
  const processing = captionBusy(project?.status);
  const stalled = processing && Date.now() - new Date(project.updated_at).getTime() >= 30 * 60 * 1000;
  const disabled = working || processing;
  const groups = useMemo(() => captionGroups(words, style.preset), [words, style.preset]);
  const cue = useMemo(() => captionAt(groups, time, style.preset), [groups, time, style.preset]);
  const apply = useCallback(data => {
    setProject(data); setWords(data.words); setStyle({ ...defaultCaptionStyle, ...data.style }); setDirty(false);
  }, []);
  const loadProjects = useCallback(async (number = 1) => {
    const response = await getCaptionProjects({ page: number });
    if (response.ok) {
      setProjects(current => number === 1 ? response.data.results : [...current, ...response.data.results]);
      setHasMore(!!response.data.next); setProjectPage(number);
    }
  }, []);
  useEffect(() => { loadProjects(); }, [loadProjects]);
  useEffect(() => {
    if (!dirty) return;
    const warn = event => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  useEffect(() => {
    let cancelled = false;
    setProject(null); setWords([]); setDirty(false); setError(""); setNotice(""); setPage(0); setTime(0);
    if (!captionId) { setLoading(false); return; }
    setLoading(true);
    getCaptionProject(captionId).then(response => {
      if (cancelled) return;
      if (response.ok) apply(response.data); else setError(response.message);
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [captionId, apply]);
  useEffect(() => {
    if (!processing || !captionId) return;
    let cancelled = false;
    let timer;
    const poll = async () => {
      const response = await getCaptionProject(captionId);
      if (cancelled) return;
      if (response.ok) {
        setError("");
        apply(response.data);
        if (!captionBusy(response.data.status)) { loadProjects(); return; }
      } else { setError("Could not check progress. Retrying…"); }
      timer = setTimeout(poll, 3000);
    };
    timer = setTimeout(poll, 2000);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [processing, captionId, apply, loadProjects]);
  // Native playback drives caption highlights; interpolation keeps word changes smooth.
  useEffect(() => {
    let frame;
    const tick = () => {
      if (player.current && !player.current.paused) setTime(player.current.currentTime);
      frame = requestAnimationFrame(tick);
    };
    if (project?.preview) frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [project?.preview]);

  const upload = async event => {
    event.preventDefault();
    if (!file || working) return;
    setWorking(true); setError("");
    try {
      const data = new FormData(); data.append("source", file);
      const response = await createCaptionProject(data);
      if (!response.ok) throw new Error(response.message);
      setFile(null); loadProjects(); navigate(`/captions/${response.data.id}/`);
    } catch (reason) { setError(reason.message); }
    finally { setWorking(false); }
  };
  const save = async () => {
    const problem = validateCaptionWords(words, project.duration);
    if (problem) throw new Error(problem);
    const response = await saveCaptionProject(project.id, { words, style });
    if (!response.ok) throw new Error(response.message);
    apply(response.data);
    return response.data;
  };
  const perform = async operation => {
    if (working || (processing && !stalled)) return;
    setWorking(true); setError(""); setNotice("");
    try {
      if (dirty || operation === "save") await save();
      if (operation === "render" || operation === "retry") {
        const response = await (operation === "render" ? renderCaptionProject(project.id) : transcribeCaptionProject(project.id));
        if (!response.ok) throw new Error(response.message);
        apply(response.data);
      } else if (operation === "srt" || operation === "download") {
        const response = await downloadCaptionProject(project.id, operation === "srt");
        if (!response.ok) throw new Error(response.message);
        const url = URL.createObjectURL(response.data);
        const link = document.createElement("a"); link.href = url;
        link.download = `${project.title.replace(/[^\p{L}\p{N}_-]/gu, "-") || "captions"}.${operation === "srt" ? "srt" : "mp4"}`;
        link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      } else setNotice("Caption changes saved.");
    } catch (reason) { setError(reason.message); }
    finally { setWorking(false); }
  };
  const seek = value => { if (player.current) { player.current.currentTime = value; setTime(value); } };
  const editWord = (index, key, value) => {
    setWords(current => current.map((word, at) => at === index ? { ...word, [key]: value } : word)); setDirty(true);
  };
  const editStyle = (key, value) => { setStyle(current => ({ ...current, [key]: value })); setDirty(true); };
  const addWord = () => {
    const nextIndex = words.findIndex(word => word.start > time);
    const index = nextIndex < 0 ? words.length : nextIndex;
    const start = Math.max(time, index > 0 ? words[index - 1].end : 0);
    const end = Math.min(project.duration, words[index]?.start ?? project.duration, start + 0.3);
    if (end <= start) { setError("There isn’t room for a word here. Adjust the neighboring times or seek to a gap first."); return; }
    setWords(current => [...current.slice(0, index), { text: "", start, end }, ...current.slice(index)]);
    setPage(Math.floor(index / PAGE_SIZE)); setDirty(true);
  };
  const leaveProject = event => {
    if (working || (dirty && !window.confirm("Discard unsaved caption changes?"))) event.preventDefault();
  };

  return <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
    {!captionId && !working && <VideoCreationMode />}
    <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div><p className="text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-300">Caption studio</p><h1 className="mt-2 text-3xl font-bold tracking-tight">Make every word stand out.</h1><p className="mt-3 max-w-2xl text-sm leading-relaxed text-gray-500 dark:text-gray-400">Upload a video, turn its speech into timed captions, and make them your own.</p></div>
      {project && <Link to="/captions/" onClick={leaveProject} className="rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-semibold dark:border-gray-700">New caption project</Link>}
    </header>
    {error && <p role="alert" className="mb-5 rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">{error}</p>}
    {notice && <p role="status" className="mb-5 text-sm text-blue-600 dark:text-blue-300">{notice}</p>}
    {loading ? <p role="status">Loading captions…</p> : !project && !captionId ? <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
      <form onSubmit={upload} className="rounded-2xl border border-gray-200 bg-white p-6 sm:p-8 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-900/30"><HiOutlineArrowUpTray className="h-6 w-6" /></div>
        <h2 className="text-xl font-bold">Start with your video</h2><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Talking clips, interviews, stories—anything with spoken audio.</p>
        <label htmlFor="caption-upload" className="mt-6 block rounded-xl border border-dashed border-gray-300 p-6 dark:border-gray-600"><span className="mb-3 block text-sm font-semibold">Choose a video</span><input id="caption-upload" type="file" accept=".mp4,.mov,.webm,.m4v" disabled={working} onChange={event => {
          const next = event.target.files?.[0]; setError("");
          if (next?.size > 100 * 1024 * 1024) { setError("Choose a video smaller than 100 MB."); setFile(null); event.target.value = ""; } else setFile(next || null);
        }} className="w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:text-blue-700" /><span className="mt-3 block text-xs text-gray-500">MP4, MOV, WebM or M4V · Up to 100 MB / 15 minutes</span></label>
        <button type="submit" disabled={!file || working} className={`${editorButton} mt-6 inline-flex items-center gap-2`}><HiOutlineSparkles />{working ? "Uploading video…" : "Generate captions"}</button>
        <p className="mt-4 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Audio is sent to OpenAI for transcription using your configured API key. Language is detected automatically. Your video's framing and sound are preserved.</p>
      </form>
      <aside className="rounded-2xl bg-gray-900 p-6 text-white"><span className="rounded-full bg-white/10 px-3 py-1 text-xs">Built for your voice</span><div className="relative mt-6 aspect-[9/12] overflow-hidden rounded-xl bg-gradient-to-br from-blue-900 to-gray-900"><CaptionLayer style="TIKTOK" cue={{ text: "YOUR WORDS.\nTHEIR ATTENTION.", active_word: 2 }} /></div><p className="mt-5 text-sm leading-relaxed text-gray-300">Word highlights that follow the audio. Clean subtitles when you want a quieter look.</p></aside>
    </div> : project && <>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-bold">{project.title}</h2><p role="status" className="mt-1 text-sm text-gray-500 dark:text-gray-400">{statusLabels[project.status]}{dirty ? " · Unsaved changes" : ""}</p></div><div className="flex flex-wrap gap-2"><button disabled={disabled || !dirty} onClick={() => perform("save")} className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-semibold disabled:opacity-40 dark:border-gray-600">Save changes</button><button disabled={disabled || !words.length} onClick={() => perform("srt")} className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-semibold disabled:opacity-40 dark:border-gray-600">Download SRT</button><button disabled={disabled || !words.length} onClick={() => perform("render")} className={editorButton}>{working ? "Working…" : "Export video"}</button></div></div>
      {project.error && <div role="alert" className="mb-5 flex flex-wrap items-center gap-3 rounded-xl bg-amber-50 p-4 text-sm text-amber-800 dark:bg-amber-900/20 dark:text-amber-200"><span>{project.error}</span>{!words.length && !processing && <button disabled={working} onClick={() => perform("retry")} className="font-semibold underline">Retry transcription</button>}</div>}
      {processing && <p className="mb-5 rounded-xl bg-blue-50 p-4 text-sm text-blue-700 dark:bg-blue-900/20 dark:text-blue-200">{project.status.includes("RENDER") ? "Export is running in the background." : "Transcription and a browser-friendly preview are being prepared."} You can leave this page and return to this project.</p>}
      {stalled && <button disabled={working} onClick={() => perform(project.status.includes("RENDER") ? "render" : "retry")} className="mb-5 rounded-xl border border-amber-300 px-4 py-2 text-sm font-semibold text-amber-700">Processing is taking too long · Retry</button>}
      {project.output && !dirty && !processing && <button onClick={() => perform("download")} disabled={working} className="mb-5 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-40"><HiOutlineArrowDownTray />Download captioned video</button>}
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-6"><div className="rounded-2xl bg-gray-900 p-4"><div className="relative mx-auto overflow-hidden rounded-xl bg-black" style={{ aspectRatio: `${project.width}/${project.height}`, maxWidth: project.height > project.width ? 330 : undefined }}>
          {project.preview ? <video ref={player} src={mediaUrl(project.preview)} controls playsInline preload="metadata" onSeeked={event => setTime(event.currentTarget.currentTime)} onTimeUpdate={event => setTime(event.currentTarget.currentTime)} onError={() => setError("Could not play the preview. Reload this project to try again.")} className="h-full w-full object-contain" /> : <div className="flex h-full min-h-[240px] items-center justify-center px-8 text-center text-sm text-gray-300">Your video preview will appear after transcription.</div>}
          <CaptionLayer cue={cue} style={style.preset} size={[project.width, project.height]} config={style} />
        </div><p className="mt-3 text-center text-xs text-gray-400">Preview · Highlights follow the transcribed word timestamps</p></div>
        <section className="overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 p-4 dark:border-gray-700"><div><h3 className="font-semibold">Words & timing</h3><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Correct a word, adjust its seconds, or jump to it in the preview.</p></div><button disabled={disabled || words.length >= 10000} onClick={addWord} className="inline-flex items-center gap-1 text-sm font-semibold text-blue-600 disabled:opacity-40"><HiOutlinePlus />Add word</button></div>
          <fieldset disabled={disabled} className="p-4"><div className="mb-2 grid grid-cols-[32px_minmax(0,1fr)_72px_72px_28px] gap-2 text-xs text-gray-500"><span>#</span><span>Word</span><span>Start (s)</span><span>End (s)</span><span /></div>
            {words.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE).map((word, at) => { const index = page * PAGE_SIZE + at; return <div key={index} className="mb-2 grid grid-cols-[32px_minmax(0,1fr)_72px_72px_28px] items-center gap-2"><button type="button" onClick={() => seek(word.start)} aria-label={`Play word ${index + 1}`} className={`text-xs tabular-nums ${time >= word.start && time < word.end ? "font-bold text-blue-600" : "text-gray-400"}`}>{index + 1}</button><input aria-label={`Word ${index + 1}`} maxLength={40} value={word.text} onChange={event => editWord(index, "text", event.target.value)} className="min-w-0 rounded-lg border border-gray-200 bg-transparent px-2 py-2 text-sm dark:border-gray-600" /><input aria-label={`Start of word ${index + 1}`} type="number" min={0} max={project.duration} step="0.01" value={Number.isFinite(word.start) ? word.start : ""} onChange={event => editWord(index, "start", event.target.value === "" ? NaN : Number(event.target.value))} className="min-w-0 rounded-lg border border-gray-200 bg-transparent px-2 py-2 text-xs dark:border-gray-600" /><input aria-label={`End of word ${index + 1}`} type="number" min={0} max={project.duration} step="0.01" value={Number.isFinite(word.end) ? word.end : ""} onChange={event => editWord(index, "end", event.target.value === "" ? NaN : Number(event.target.value))} className="min-w-0 rounded-lg border border-gray-200 bg-transparent px-2 py-2 text-xs dark:border-gray-600" /><button aria-label={`Remove word ${index + 1}`} onClick={() => { setWords(current => current.filter((_, i) => i !== index)); setDirty(true); setPage(Math.min(page, Math.max(0, Math.ceil((words.length - 1) / PAGE_SIZE) - 1))); }} className="text-gray-400 hover:text-red-500"><HiOutlineTrash className="h-4 w-4" /></button></div>; })}
            {!words.length && <p className="py-4 text-sm text-gray-500">{processing ? "Words will appear here when transcription finishes." : "No words yet. Add a word or retry transcription."}</p>}
          </fieldset>{words.length > PAGE_SIZE && <div className="flex items-center justify-between border-t border-gray-100 p-4 text-sm dark:border-gray-700"><button disabled={page === 0} onClick={() => setPage(page - 1)} className="disabled:opacity-40">Previous</button><span>{page + 1} / {Math.ceil(words.length / PAGE_SIZE)}</span><button disabled={(page + 1) * PAGE_SIZE >= words.length} onClick={() => setPage(page + 1)} className="disabled:opacity-40">Next</button></div>}
        </section></div>
        <fieldset disabled={disabled} className="space-y-5 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800"><h3 className="font-semibold">Make it yours</h3><label className="block text-sm">Caption style<select value={style.preset} onChange={event => editStyle("preset", event.target.value)} className={`${editorInput} mt-2`}><option value="TIKTOK">TikTok · word highlights</option><option value="CLASSIC">Classic · simple subtitles</option></select></label><FontPicker value={style.font} onChange={font => editStyle("font", font)} /><label className="block text-sm">Text size <span className="float-right text-gray-400">{style.size}</span><input type="range" min={3} max={9} value={style.size} onChange={event => editStyle("size", Number(event.target.value))} className="mt-3 w-full accent-blue-600" /></label><div className="grid grid-cols-2 gap-4"><label className="text-sm">Text color<input type="color" value={style.color} onChange={event => editStyle("color", event.target.value)} className="mt-2 block h-10 w-full rounded-lg" /></label><label className="text-sm">Highlight<input type="color" disabled={style.preset === "CLASSIC"} value={style.highlight} onChange={event => editStyle("highlight", event.target.value)} className="mt-2 block h-10 w-full rounded-lg disabled:opacity-40" /></label></div><label className="block text-sm">Position<select value={style.position} onChange={event => editStyle("position", event.target.value)} className={`${editorInput} mt-2`}><option value="bottom">Lower area</option><option value="middle">Center</option><option value="top">Upper area</option></select></label><p className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">Portrait captions leave room near the bottom for social app controls. Transcription may need corrections—review the words before exporting.</p></fieldset>
      </div>
    </>}
    <section className="mt-10 border-t border-gray-200 pt-6 dark:border-gray-700"><h2 className="mb-4 text-lg font-semibold">Your caption projects</h2>{projects.length ? <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{projects.map(item => <Link key={item.id} to={`/captions/${item.id}/`} onClick={leaveProject} className={`rounded-xl border bg-white p-4 transition hover:border-blue-400 dark:bg-gray-800 ${item.id === captionId ? "border-blue-500" : "border-gray-200 dark:border-gray-700"}`}><span className="block truncate text-sm font-semibold">{item.title}</span><span className="mt-2 block text-xs text-gray-500 dark:text-gray-400">{statusLabels[item.status]} · {Math.round(item.duration)} seconds</span></Link>)}</div> : <p className="text-sm text-gray-500">Your saved projects will appear here.</p>}{hasMore && <button onClick={() => loadProjects(projectPage + 1)} className="mt-4 text-sm font-semibold text-blue-600">Load more projects</button>}</section>
  </main>;
}
