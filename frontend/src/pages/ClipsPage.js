import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { HiOutlineScissors, HiOutlineArrowUpTray, HiOutlineSparkles, HiOutlineFilm, HiOutlineDocumentText, HiOutlinePlus, HiOutlineArrowDownTray, HiOutlineArrowPath, HiOutlineArrowLeft } from "react-icons/hi2";
import { subscribeUpdates } from "../api/subscribeUpdates";
import { ClipProjectCard } from "../components/ClipProjectCard";
import { ClipSelectionOptions, clipFocusOptions, clipSelectionModes } from "../components/ClipSelectionOptions";
import { useDebounce } from "../hooks/useDebounce";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";
import { FullVideoTranscript } from "../components/FullVideoTranscript";
import { ClipCard } from "../components/ClipCard";
import { ClipEditor } from "../components/ClipEditor";
import { editorButton, editorInput } from "../components/ui/EditorDialog";
import { createClip, createClipProject, deleteClip, deleteClipProject, downloadClip, exportClips, getClipProject, getClipProjectProgress, getClip, getClipProjects, retryClipProject, saveClip } from "../api/apiService";
import { clipBusy, reconcileClipProgress, formatTime, minutesToSeconds, projectBusy, projectStatus } from "../utils/clips";

export default function ClipsPage() {
  useAxiosPrivate();
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [creating, setCreating] = useState(false);
  const [projectSearch, setProjectSearch] = useState("");
  const [projectFilter, setProjectFilter] = useState("");
  const [projectTotal, setProjectTotal] = useState(0);
  const search = useDebounce(projectSearch, 300);
  const [projects, setProjects] = useState([]);
  const [page, setPage] = useState(1);
  const [next, setNext] = useState(null);
  const [sourceMode, setSourceMode] = useState("file");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [file, setFile] = useState(null);
  const [extractionPrompt, setExtractionPrompt] = useState("");
  const [clipFocus, setClipFocus] = useState("general");
  const [selectionMode, setSelectionMode] = useState("balanced");
  const [rangeStart, setRangeStart] = useState(0);
  const [rangeEnd, setRangeEnd] = useState("");
  const [count, setCount] = useState(5);
  const [minDuration, setMinDuration] = useState("0.5");
  const [maxDuration, setMaxDuration] = useState("1");
  const [selected, setSelected] = useState([]);
  const [workspaceView, setWorkspaceView] = useState("clips");
  const [notice, setNotice] = useState("");
  const [editing, setEditing] = useState(null);
  const drafts = useRef(new Map());
  const [editorSaving, setEditorSaving] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleteMode, setDeleteMode] = useState(false);
  const latest = useRef(null);
  latest.current = project;
  const revision = useRef(0);
  const route = useRef(projectId);
  route.current = projectId;
  const load = useCallback(async () => {
    const id = projectId;
    const requestRevision = ++revision.current;
    const result = await getClipProject(id);
    if (route.current !== id || requestRevision !== revision.current) return;
    if (result.ok) setProject(result.data); else setError(result.message);
    setLoading(false);
  }, [projectId]);
  useEffect(() => {
    setWorkspaceView("clips"); setNotice(""); drafts.current.clear(); setEditorSaving(false); setProject(null); setEditing(null); setSelected([]); setError(""); setDeleteMode(false); setLoading(true);
    let active = true;
    if (projectId) load();
    else getClipProjects(page, { search, status: projectFilter }).then(result => { if (!active) return; if (result.ok) { setProjectTotal(result.data.count ?? result.data.results.length); setProjects(result.data.results); setNext(result.data.next); } else setError(result.message); setLoading(false); });
    return () => { active = false; };
  }, [projectId, page, load, search, projectFilter]);
  const busy = projectBusy(project?.status);
  const exporting = project?.clips.some(clip => clipBusy(clip.status));
  useEffect(() => {
    if (!projectId) return;
    let active = true;
    const unsubscribe = subscribeUpdates(`clips/${encodeURIComponent(projectId)}/events/`, {
      load: () => getClipProjectProgress(projectId),
      onUpdate: async progress => {
        const requestRevision = ++revision.current;
        try {
          const nextProject = await reconcileClipProgress(latest.current, progress, { loadProject: () => getClipProject(projectId), loadClip: id => getClip(projectId, id) });
          if (active && route.current === projectId && requestRevision === revision.current) { setProject(nextProject); setLoading(false); }
        } catch (failure) { if (active) setError(failure.message); }
      },
      onError: failure => { if (active) { setError(failure.message || "Could not refresh clip progress. Reload to reconnect."); setLoading(false); } },
    });
    const refresh = () => { if (document.visibilityState === "visible") load(); };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => { active = false; unsubscribe(); window.removeEventListener("focus", refresh); document.removeEventListener("visibilitychange", refresh); };
  }, [projectId, load]);
  const upload = async event => {
    event.preventDefault(); setError("");
    if (sourceMode === "file" && !file) { setError("Choose a video first."); return; }
    if (sourceMode === "file" && file.size > 1024 ** 3) { setError("Choose a video up to 1 GB."); return; }
    if (sourceMode === "youtube" && !youtubeUrl.trim()) { setError("Enter a YouTube link first."); return; }
    const startSeconds = rangeStart === "" ? NaN : minutesToSeconds(rangeStart);
    const endSeconds = rangeEnd === "" ? null : minutesToSeconds(rangeEnd);
    const minSeconds = Math.round(minutesToSeconds(minDuration));
    const maxSeconds = Math.round(minutesToSeconds(maxDuration));
    if (!Number.isFinite(minSeconds) || !Number.isFinite(maxSeconds) || minSeconds < 10 || maxSeconds > 180) { setError("Choose clip lengths between 1/6 and 3 minutes."); return; }
    if (maxSeconds < minSeconds) { setError("Maximum length must be at least the minimum length."); return; }
    if (!Number.isFinite(startSeconds) || startSeconds < 0 || (endSeconds !== null && (!Number.isFinite(endSeconds) || endSeconds - startSeconds < minSeconds))) { setError("Choose a range at least as long as the minimum clip length."); return; }
    setWorking(true);
    const data = new FormData(); data.append("range_start", startSeconds); if (rangeEnd !== "") data.append("range_end", endSeconds); if (sourceMode === "file") data.append("source", file); else data.append("youtube_url", youtubeUrl.trim()); data.append("clip_count", count); data.append("min_duration", minSeconds); data.append("max_duration", maxSeconds); if (extractionPrompt.trim()) data.append("extraction_prompt", extractionPrompt.trim());
    data.append("clip_focus", clipFocus); data.append("selection_mode", selectionMode);
    const result = await createClipProject(data);
    setWorking(false);
    if (result.ok) navigate(`/clips/${result.data.id}/`); else setError(result.message);
  };
  const perform = async action => {
    setWorking(true); setError("");
    const result = await action();
    setWorking(false);
    if (!result.ok) { setError(result.message); return false; }
    await load();
    return result;
  };
  const add = async () => {
    const result = await perform(() => createClip(project.id, { title: "New clip", start: project.range_start ?? 0, end: Math.min((project.range_start ?? 0) + 60, project.range_end ?? project.duration) }));
    if (result) { setWorkspaceView("clips"); setEditing(result.data); }
  };
  const addFromTranscript = async range => {
    const result = await perform(() => createClip(project.id, range));
    if (result) { setWorkspaceView("clips"); setEditing(result.data); }
    return !!result;
  };
  const render = async ids => {
    const result = await perform(() => exportClips(project.id, ids));
    if (result && result.data.some(clip => clip.status === "FAILED")) setError("Some exports could not be queued. Retry the clips marked as needing attention.");
  };
  const download = async clip => {
    setWorking(true); setError("");
    const result = await downloadClip(project.id, clip.id);
    setWorking(false);
    if (!result.ok) { setError(result.message); return; }
    const url = URL.createObjectURL(result.data);
    const link = document.createElement("a"); link.href = url; link.download = `${clip.title.replace(/[^\p{L}\p{N} _-]/gu, "").slice(0, 80) || "clip"}.mp4`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const removeProject = async () => {
    setWorking(true); const result = await deleteClipProject(project.id); setWorking(false);
    if (result.ok) navigate("/clips/"); else setError(result.message);
  };
  const stale = project?.can_retry || (busy && Date.now() - new Date(project.updated_at).getTime() > 3 * 3600000);
  return <main className="clips-workspace mx-auto min-w-0 max-w-[1440px] px-4 py-8 sm:px-6 [&_input]:text-base [&_textarea]:text-base [&_select]:text-base sm:[&_input]:text-sm sm:[&_textarea]:text-sm sm:[&_select]:text-sm">
    <header className="mb-8 flex flex-wrap items-start justify-between gap-4 border-b border-gray-200 pb-7 dark:border-gray-700"><div><p className="mb-2 flex items-center gap-2 text-sm font-semibold text-rose-600 dark:text-rose-300"><HiOutlineScissors />Long video → Shorts</p><h1 className="break-words text-2xl font-bold tracking-tight sm:text-3xl">{project?.title || (creating ? "Start a new project" : "Your clipping studio")}</h1><p className="mt-3 max-w-2xl text-sm leading-relaxed text-gray-500 dark:text-gray-400">{project ? "Review your excerpts, choose portrait framing, and make every word readable." : creating ? "Bring a long video. We’ll help you find the moments worth sharing." : "Your videos, highlights, and finished clips. Pick up where you left off."}</p></div><Link to={projectId ? "/clips/" : "/"} className="text-sm font-semibold text-blue-600 dark:text-blue-300">{projectId ? "All clipping projects" : "All creation tools"}</Link>{!projectId && <button type="button" onClick={() => setCreating(value => !value)} className={`${editorButton} flex items-center gap-2`}>{creating ? <HiOutlineArrowLeft aria-hidden="true" /> : <HiOutlinePlus aria-hidden="true" />}{creating ? "Back to projects" : "New project"}</button>}</header>
    {error && <p role="alert" className="mb-5 break-words rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">{error}</p>}
    {notice && <p role="status" className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300">{notice}</p>}
    {!projectId && creating && <>
      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
      <form onSubmit={upload} className="clip-panel min-w-0 rounded-2xl border border-gray-200 bg-white p-5 sm:p-7 dark:border-gray-700 dark:bg-gray-800"><fieldset disabled={working} className="min-w-0">
        <div className="mb-6 flex items-start gap-3"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-sm font-bold text-blue-600 dark:bg-blue-950 dark:text-blue-300">01</span><div><h2 className="text-lg font-bold">Add your source</h2><p className="mt-1 text-sm text-gray-500">A video, a few preferences, and you're ready.</p></div></div>
        <div role="group" aria-label="Video source" className="mb-5 flex gap-2"><button type="button" aria-pressed={sourceMode === "file"} onClick={() => setSourceMode("file")} className={`min-h-11 flex-1 rounded-xl border px-3 text-sm font-semibold ${sourceMode === "file" ? "border-rose-400 bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-200" : "border-gray-200 dark:border-gray-600"}`}>Upload a file</button><button type="button" aria-pressed={sourceMode === "youtube"} onClick={() => setSourceMode("youtube")} className={`min-h-11 flex-1 rounded-xl border px-3 text-sm font-semibold ${sourceMode === "youtube" ? "border-rose-400 bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-200" : "border-gray-200 dark:border-gray-600"}`}>YouTube link</button></div>
        {sourceMode === "youtube" ? <label className="block text-sm font-medium">YouTube video link<input type="url" value={youtubeUrl} onChange={event => setYoutubeUrl(event.target.value)} placeholder="https://www.youtube.com/watch?v=…" className={`${editorInput} mt-2`} /><span className="mt-2 block text-xs font-normal leading-relaxed text-gray-500">One public video or Short · Up to 1 GB. Use a video you own or have permission to edit. Private or restricted videos may require a file upload.</span></label> : <label className="flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed border-gray-200 bg-gray-50 px-5 py-8 text-center dark:border-gray-600 dark:bg-gray-900"><HiOutlineArrowUpTray className="mb-3 h-7 w-7 text-rose-500" /><span className="font-semibold">{file ? file.name : "Choose your long video"}</span><span className="mt-2 text-xs text-gray-500">MP4, MOV, WebM, M4V · Up to 1 GB · Spoken audio required</span><input aria-label="Source video" type="file" accept=".mp4,.mov,.webm,.m4v" onChange={event => setFile(event.target.files?.[0] || null)} className="mt-4 w-full min-w-0 max-w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:font-semibold file:text-blue-600" /></label>}
        <details className="mt-5 rounded-xl border border-gray-200 p-4 dark:border-gray-600"><summary className="cursor-pointer text-sm font-semibold">Process only part of the video (optional)</summary><p className="mt-2 text-xs leading-relaxed text-gray-500">Only this section is transcribed and searched for clips. Enter decimal minutes (1.5 = 1 minute 30 seconds) on the original video timeline. Leave the end blank to process until the video ends.</p><div className="mt-3 grid gap-4 sm:grid-cols-2"><label className="text-sm">Process from (minutes)<input type="number" min={0} step="any" required value={rangeStart} onChange={event => setRangeStart(event.target.value)} className={`${editorInput} mt-2`} /></label><label className="text-sm">Process until (minutes)<input type="number" min={0} step="any" value={rangeEnd} placeholder="End of video" onChange={event => setRangeEnd(event.target.value)} className={`${editorInput} mt-2`} /></label></div></details>
        <ClipSelectionOptions focus={clipFocus} mode={selectionMode} onFocusChange={setClipFocus} onModeChange={setSelectionMode} />
        <label className="mt-5 block text-sm font-medium">What kind of clips do you want? <span className="font-normal text-gray-500">(optional)</span><textarea maxLength={2000} rows={3} value={extractionPrompt} onChange={event => setExtractionPrompt(event.target.value)} placeholder="For example: practical business advice, funny moments, or explanations for beginners" className={`${editorInput} mt-2`} /><span className="mt-2 block text-xs font-normal text-gray-500">Leave blank to use your clip focus. All modes use the spoken transcript; they do not analyse visuals or voice delivery.</span></label>
        <div className="mt-5 grid gap-4 sm:grid-cols-3"><label className="text-sm">Number of suggestions<input type="number" min={1} max={10} required value={count} onChange={event => setCount(Number(event.target.value))} className={`${editorInput} mt-2`} /></label><label className="text-sm">Minimum clip length (minutes)<input type="number" min={1 / 6} max={3} step="any" required value={minDuration} onChange={event => setMinDuration(event.target.value)} className={`${editorInput} mt-2`} /></label><label className="text-sm">Maximum clip length (minutes)<input type="number" min={1 / 6} max={3} step="any" required value={maxDuration} onChange={event => setMaxDuration(event.target.value)} className={`${editorInput} mt-2`} /></label></div>
        <p className="my-4 text-xs leading-relaxed text-gray-500">Available YouTube captions are checked first; otherwise your audio is transcribed locally by default. Highlights are suggested by AI. Saved transcripts are reused when possible. Provider charges apply to highlight suggestions and optional OpenAI transcription.</p>
        <button type="submit" disabled={(sourceMode === "file" ? !file : !youtubeUrl.trim()) || working} className={editorButton}>{working ? "Saving your source…" : "Find short clips"}</button>
      </fieldset></form>
      <aside className="clip-panel hidden lg:block rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"><p className="text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-300">From long to shareable</p><h2 className="mt-3 text-xl font-bold">Make room for the good parts.</h2><ol className="mt-6 space-y-6">{[{ title: "Bring your video", text: "Interviews, podcasts, and talks work best. Keep the original voice and context." }, { title: "Find the moments", text: "Let AI suggest highlights, or search the transcript for a topic you have in mind." }, { title: "Make it yours", text: "Trim, frame, caption, and export portrait clips ready to share." }].map((step, index) => <li key={step.title} className="flex gap-3"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-gray-200 text-xs font-semibold text-gray-400 dark:border-gray-600">{index + 1}</span><div><h3 className="text-sm font-semibold">{step.title}</h3><p className="mt-1 text-xs leading-relaxed text-gray-500">{step.text}</p></div></li>)}</ol><p className="mt-6 border-t border-gray-200 pt-4 text-xs leading-relaxed text-gray-500 dark:border-gray-700">Want to save on processing? Choose only the section you need. Existing transcripts stay available for future projects.</p></aside>
      </div>
    </>}
    {!projectId && !creating && <section aria-label="Your clipping projects">
      <div className="clip-panel mb-6 flex flex-wrap items-end gap-4 rounded-2xl border border-gray-200 bg-white p-4 sm:p-5 dark:border-gray-700 dark:bg-gray-800"><label className="min-w-0 flex-1 text-sm font-medium">Search projects<input type="search" maxLength={200} value={projectSearch} onChange={event => { setProjectSearch(event.target.value); setPage(1); }} placeholder="Search by project name…" className={`${editorInput} mt-2`} /></label><label className="w-full text-sm font-medium sm:w-48">Status<select value={projectFilter} onChange={event => { setProjectFilter(event.target.value); setPage(1); }} className={`${editorInput} mt-2`}><option value="">All projects</option><option value="READY">Ready to review</option><option value="PROCESSING">Processing</option><option value="FAILED">Needs attention</option></select></label></div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-bold">Your clipping projects <span className="ml-1 text-sm font-normal text-gray-400">{projectTotal}</span></h2><p className="text-xs text-gray-500">Most recent first</p></div>
      {loading ? <p role="status" className="py-12 text-center text-sm text-gray-500">Loading projects…</p> : !projects.length ? <div className="clip-panel rounded-2xl border border-dashed border-gray-300 bg-white px-6 py-16 text-center dark:border-gray-600 dark:bg-gray-800"><HiOutlineFilm aria-hidden="true" className="mx-auto mb-4 h-10 w-10 text-blue-500" /><h3 className="text-xl font-bold">{projectSearch || projectFilter ? "No matching projects" : "Your next great clip starts here"}</h3><p className="mx-auto mt-3 max-w-md text-sm text-gray-500">{projectSearch || projectFilter ? "Try another name or clear the filters to see your projects." : "Add a video or YouTube link to create your first set of highlights."}</p><button type="button" onClick={() => { if (projectSearch || projectFilter) { setProjectSearch(""); setProjectFilter(""); setPage(1); } else setCreating(true); }} className={`${editorButton} mt-6`}>{projectSearch || projectFilter ? "Clear filters" : "Create your first project"}</button></div> : <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">{projects.map(item => <ClipProjectCard key={item.id} project={item} />)}</div>}
      <div className="mt-6 flex items-center justify-between gap-4 text-sm">{page > 1 ? <button onClick={() => setPage(value => value - 1)} className="min-h-11 rounded-xl border border-gray-200 px-4 dark:border-gray-600">Previous projects</button> : <span />}{next && <button onClick={() => setPage(next)} className="min-h-11 rounded-xl border border-gray-200 px-4 dark:border-gray-600">More projects</button>}</div>
    </section>}
    {projectId && loading && <p role="status">Loading clipping project…</p>}
    {project && <>
      <section aria-label="Project overview" className="clip-panel mb-6 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800"><div className="flex flex-wrap items-center justify-between gap-4"><div><p role="status" className="flex items-center gap-2 text-sm font-semibold"><span className={`h-2 w-2 rounded-full ${busy ? "animate-pulse bg-blue-500" : project.status === "FAILED" ? "bg-amber-500" : "bg-emerald-500"}`} />{projectStatus[project.status]}</p><div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs text-gray-500"><span>{project.duration > 0 ? `${formatTime(project.duration)} source` : "Source duration pending…"}</span><span>{project.clips.length} clips</span>{project.transcript_source && <span>Transcript: {project.transcript_source}</span>}<span>{project.clips.filter(clip => clip.status === "COMPLETED").length} exports ready</span><span>{project.min_duration}–{project.max_duration}s preferred length</span></div></div><div className="flex flex-wrap items-center gap-3"><button type="button" onClick={load} disabled={working} className="flex min-h-11 items-center gap-2 rounded-xl border border-gray-200 px-3 text-xs font-semibold text-gray-500 dark:border-gray-600"><HiOutlineArrowPath aria-hidden="true" />Refresh progress</button>{(project.status === "FAILED" || stale) && <button disabled={working} onClick={() => perform(() => retryClipProject(project.id))} className={editorButton}>Retry processing</button>}</div></div></section>
      {project.extraction_prompt && <p className="mb-5 border-l-2 border-blue-400 pl-4 text-sm text-gray-500"><span className="font-semibold">Looking for: </span>{project.extraction_prompt}</p>}
      <p className="mb-5 text-sm text-gray-500" aria-label="Saved selection preferences">{clipFocusOptions.find(option => option.value === (project.clip_focus || "general"))?.label} · {clipSelectionModes.find(option => option.value === (project.selection_mode || "balanced"))?.label} selection. Used for retries and AI transcript search.</p>
      {project.error && <p role="alert" className="mb-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-700 dark:bg-amber-950 dark:text-amber-300">{project.error}</p>}
      {busy && <p className="mb-6 text-sm text-gray-500">You can leave this page and return later. Completed transcription chunks are saved for retries.</p>}
      {(project.range_start > 0 || project.range_end != null) && <p className="mb-4 text-sm text-gray-500">Processing range: {formatTime(project.range_start)}–{project.range_end != null || project.duration > 0 ? formatTime(project.range_end ?? project.duration) : "End of video"}. Clip times use the original video timeline.</p>}
      <div role="group" aria-label="Workspace views" className="mb-6 flex flex-wrap gap-2 border-b border-gray-200 pb-3 dark:border-gray-700">{[{ id: "clips", label: "Clips", Icon: HiOutlineFilm }, { id: "transcript", label: "Transcript & AI search", Icon: HiOutlineDocumentText }].map(({ id, label, Icon }) => <button key={id} type="button" aria-pressed={workspaceView === id} disabled={editorSaving} onClick={() => setWorkspaceView(id)} className={`flex min-h-11 items-center gap-2 rounded-xl px-4 text-sm font-semibold ${workspaceView === id ? "bg-blue-600 text-white shadow-sm" : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"}`}><Icon aria-hidden="true" />{label}{id === "clips" && <span className="rounded-md bg-white/15 px-1.5 py-0.5 text-xs">{project.clips.length}</span>}</button>)}</div>
      <div hidden={workspaceView !== "transcript"}>
        <FullVideoTranscript projectId={project.id} key={project.id} title={project.title} words={project.words} partial={project.range_start > 0 || project.range_end != null} expanded onCreateClip={!busy && project.clips.length < 20 ? addFromTranscript : undefined} disabled={working || editorSaving} />
      </div>
      <div hidden={workspaceView !== "clips"}>
        {!busy && <div className="mb-5 flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">Review your clips</h2><p className="mt-1 text-xs text-gray-500">Choose a moment, make it yours, then export.</p></div><div className="flex w-full flex-wrap gap-2 sm:w-auto"><button disabled={working || !!editing || !selected.length} onClick={() => render(selected)} className={`${editorButton} flex items-center gap-2`}><HiOutlineArrowDownTray aria-hidden="true" />Export selected ({selected.length})</button><button disabled={working || !!editing || project.clips.length >= 20} onClick={add} className="flex min-h-11 items-center gap-2 rounded-xl border border-gray-200 px-4 text-sm font-semibold text-gray-600 dark:border-gray-600 dark:text-gray-300"><HiOutlinePlus aria-hidden="true" />Add clip manually</button></div></div>}
        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <div className="flex min-w-0 gap-3 overflow-x-auto pb-3 lg:sticky lg:top-6 lg:block lg:max-h-[78vh] lg:space-y-3 lg:overflow-y-auto lg:pr-2" aria-label="Clip list">
            {!busy && !project.clips.length && <p className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500 dark:border-gray-700">No suitable highlights yet. Find a moment in the transcript or add a clip manually.</p>}
            {project.clips.map((clip, index) => <ClipCard key={clip.id} projectId={project.id} clip={clip} index={index} active={editing?.id === clip.id} selected={selected.includes(clip.id)} working={working} busy={busy} editorSaving={editorSaving} hasEditor={!!editing} onSelect={checked => setSelected(current => checked ? [...current, clip.id] : current.filter(id => id !== clip.id))} onEdit={() => { setNotice(""); setEditing(clip); }} onDownload={() => download(clip)} onExport={() => render([clip.id])} onRemove={async () => { if (await perform(() => deleteClip(project.id, clip.id))) setSelected(current => current.filter(id => id !== clip.id)); }} onHashtagsSaved={load} onUploadedChange={uploaded => perform(() => saveClip(project.id, clip.id, { uploaded, revision: clip.revision }))} />)}
          </div>
          <div className="min-w-0">
            {editing && <ClipEditor key={editing.id} project={project} clip={editing} initialDraft={drafts.current.get(editing.id)} onDraftChange={draft => drafts.current.set(editing.id, draft)} onWorkingChange={setEditorSaving} onClose={() => { drafts.current.delete(editing.id); setEditing(null); }} onSaved={() => { drafts.current.delete(editing.id); setEditing(null); setNotice("Clip saved. Choose another clip to keep editing, or export when you’re ready."); load(); }} />}
            {!editing && <section className="clip-panel flex min-h-[400px] flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 bg-white px-6 py-12 text-center dark:border-gray-600 dark:bg-gray-800"><div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-300"><HiOutlineScissors className="h-8 w-8" aria-hidden="true" /></div><p className="mb-2 text-xs font-semibold uppercase tracking-widest text-gray-400">Your editing space</p><h2 className="text-xl font-bold">Choose a clip to start</h2><p className="mt-3 max-w-sm text-sm leading-relaxed text-gray-500">Preview the moment, adjust the framing, and polish the captions. Your drafts stay with each clip when you switch.</p><button onClick={() => setWorkspaceView("transcript")} className="mt-6 flex min-h-11 items-center gap-2 rounded-xl border border-gray-200 px-4 text-sm font-semibold text-blue-600 dark:border-gray-600 dark:text-blue-300"><HiOutlineSparkles aria-hidden="true" />Find a moment with AI</button></section>}
          </div>
        </div>
      </div>
      {!busy && !exporting && !editing && <div className="mt-9 border-t border-gray-200 pt-5 text-sm dark:border-gray-700">{deleteMode ? <div className="flex flex-wrap items-center gap-4"><p>Delete this upload and all its clips?</p><button disabled={working} onClick={removeProject} className="font-semibold text-red-600">Delete project</button><button disabled={working} onClick={() => setDeleteMode(false)}>Keep project</button></div> : <button onClick={() => setDeleteMode(true)} className="text-gray-400">Delete clipping project</button>}</div>}
    </>}
  </main>;
}
