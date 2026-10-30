import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { HiOutlineScissors, HiOutlineArrowUpTray } from "react-icons/hi2";
import { subscribeUpdates } from "../api/subscribeUpdates";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";
import { FullVideoTranscript } from "../components/FullVideoTranscript";
import { ClipHashtags } from "../components/ClipHashtags";
import { ClipEditor } from "../components/ClipEditor";
import { editorButton, editorInput } from "../components/ui/EditorDialog";
import { createClip, createClipProject, deleteClip, deleteClipProject, downloadClip, exportClips, getClipProject, getClipProjectProgress, getClip, getClipProjects, retryClipProject } from "../api/apiService";
import { clipBusy, clipStalled, clipStatus, reconcileClipProgress, formatTime, projectBusy, projectStatus } from "../utils/clips";

export default function ClipsPage() {
  useAxiosPrivate();
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [projects, setProjects] = useState([]);
  const [page, setPage] = useState(1);
  const [next, setNext] = useState(null);
  const [sourceMode, setSourceMode] = useState("file");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [file, setFile] = useState(null);
  const [extractionPrompt, setExtractionPrompt] = useState("");
  const [count, setCount] = useState(5);
  const [minDuration, setMinDuration] = useState(30);
  const [maxDuration, setMaxDuration] = useState(60);
  const [selected, setSelected] = useState([]);
  const [editing, setEditing] = useState(null);
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
    setProject(null); setEditing(null); setSelected([]); setError(""); setDeleteMode(false); setLoading(true);
    let active = true;
    if (projectId) load();
    else getClipProjects(page).then(result => { if (!active) return; if (result.ok) { setProjects(result.data.results); setNext(result.data.next); } else setError(result.message); setLoading(false); });
    return () => { active = false; };
  }, [projectId, page, load]);
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
    if (maxDuration < minDuration) { setError("Maximum length must be at least the minimum length."); return; }
    setWorking(true);
    const data = new FormData(); if (sourceMode === "file") data.append("source", file); else data.append("youtube_url", youtubeUrl.trim()); data.append("clip_count", count); data.append("min_duration", minDuration); data.append("max_duration", maxDuration); if (extractionPrompt.trim()) data.append("extraction_prompt", extractionPrompt.trim());
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
    const result = await perform(() => createClip(project.id, { title: "New clip", start: 0, end: Math.min(60, project.duration) }));
    if (result) setEditing(result.data);
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
  return <main className="mx-auto min-w-0 max-w-6xl px-4 py-8 sm:px-6 [&_input]:text-base [&_textarea]:text-base [&_select]:text-base sm:[&_input]:text-sm sm:[&_textarea]:text-sm sm:[&_select]:text-sm">
    <header className="mb-7 flex flex-wrap items-start justify-between gap-4"><div><p className="mb-2 flex items-center gap-2 text-sm font-semibold text-rose-600 dark:text-rose-300"><HiOutlineScissors />Long video → Shorts</p><h1 className="break-words text-2xl font-bold tracking-tight sm:text-3xl">{project?.title || "Find the moments worth sharing"}</h1><p className="mt-3 max-w-2xl text-sm leading-relaxed text-gray-500 dark:text-gray-400">{project ? "Review your excerpts, choose portrait framing, and make every word readable." : "Turn interviews, podcasts, and talks into short portrait clips. Review AI suggestions and make the final cut."}</p></div><Link to={projectId ? "/clips/" : "/"} className="text-sm font-semibold text-blue-600 dark:text-blue-300">{projectId ? "All clipping projects" : "All creation tools"}</Link></header>
    {error && <p role="alert" className="mb-5 break-words rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">{error}</p>}
    {!projectId && <>
      <form onSubmit={upload} className="rounded-2xl border border-gray-200 bg-white p-5 sm:p-7 dark:border-gray-700 dark:bg-gray-800"><fieldset disabled={working} className="min-w-0">
        <div role="group" aria-label="Video source" className="mb-5 flex gap-2"><button type="button" aria-pressed={sourceMode === "file"} onClick={() => setSourceMode("file")} className={`min-h-11 flex-1 rounded-xl border px-3 text-sm font-semibold ${sourceMode === "file" ? "border-rose-400 bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-200" : "border-gray-200 dark:border-gray-600"}`}>Upload a file</button><button type="button" aria-pressed={sourceMode === "youtube"} onClick={() => setSourceMode("youtube")} className={`min-h-11 flex-1 rounded-xl border px-3 text-sm font-semibold ${sourceMode === "youtube" ? "border-rose-400 bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-200" : "border-gray-200 dark:border-gray-600"}`}>YouTube link</button></div>
        {sourceMode === "youtube" ? <label className="block text-sm font-medium">YouTube video link<input type="url" value={youtubeUrl} onChange={event => setYoutubeUrl(event.target.value)} placeholder="https://www.youtube.com/watch?v=…" className={`${editorInput} mt-2`} /><span className="mt-2 block text-xs font-normal leading-relaxed text-gray-500">One public video or Short · Up to 1 GB / 2 hours. Use a video you own or have permission to edit. Private or restricted videos may require a file upload.</span></label> : <label className="flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed border-gray-200 bg-gray-50 px-5 py-8 text-center dark:border-gray-600 dark:bg-gray-900"><HiOutlineArrowUpTray className="mb-3 h-7 w-7 text-rose-500" /><span className="font-semibold">Choose your long video</span><span className="mt-2 text-xs text-gray-500">MP4, MOV, WebM, M4V · Up to 1 GB and 2 hours · Spoken audio required</span><input aria-label="Source video" type="file" accept=".mp4,.mov,.webm,.m4v" onChange={event => setFile(event.target.files?.[0] || null)} className="mt-4 w-full min-w-0 max-w-full text-sm" /></label>}
        <label className="mt-5 block text-sm font-medium">What kind of clips do you want? <span className="font-normal text-gray-500">(optional)</span><textarea maxLength={2000} rows={3} value={extractionPrompt} onChange={event => setExtractionPrompt(event.target.value)} placeholder="For example: practical business advice, funny moments, or explanations for beginners" className={`${editorInput} mt-2`} /><span className="mt-2 block text-xs font-normal text-gray-500">Leave blank to find general highlights. Suggestions use the video's spoken content.</span></label>
        <div className="mt-5 grid gap-4 sm:grid-cols-3"><label className="text-sm">Number of suggestions<input type="number" min={1} max={10} required value={count} onChange={event => setCount(Number(event.target.value))} className={`${editorInput} mt-2`} /></label><label className="text-sm">Minimum clip length (seconds)<input type="number" min={10} max={180} required value={minDuration} onChange={event => setMinDuration(Number(event.target.value))} className={`${editorInput} mt-2`} /></label><label className="text-sm">Maximum clip length (seconds)<input type="number" min={10} max={180} required value={maxDuration} onChange={event => setMaxDuration(Number(event.target.value))} className={`${editorInput} mt-2`} /></label></div>
        <p className="my-4 text-xs leading-relaxed text-gray-500">Audio is sent to OpenAI for transcription. Transcript excerpts are sent to your configured text provider to suggest highlights. Provider charges apply. Suggestions may need adjustment.</p>
        <button type="submit" disabled={(sourceMode === "file" ? !file : !youtubeUrl.trim()) || working} className={editorButton}>{working ? "Saving your source…" : "Find short clips"}</button>
      </fieldset></form>
      <section className="mt-9"><h2 className="mb-4 text-lg font-bold">Your clipping projects</h2>{loading ? <p role="status">Loading projects…</p> : !projects.length ? <p className="text-sm text-gray-500">Your uploaded videos and clips will appear here.</p> : <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{projects.map(item => <Link key={item.id} to={`/clips/${item.id}/`} className="rounded-xl border border-gray-200 bg-white p-5 hover:border-rose-400 dark:border-gray-700 dark:bg-gray-800"><h3 className="truncate font-semibold">{item.title}</h3><p className="mt-2 text-xs text-gray-500">{formatTime(item.duration)} · {projectStatus[item.status]}</p></Link>)}</div>}<div className="mt-5 flex gap-4 text-sm">{page > 1 && <button onClick={() => setPage(value => value - 1)}>Previous projects</button>}{next && <button onClick={() => setPage(next)}>More projects</button>}</div></section>
    </>}
    {projectId && loading && <p role="status">Loading clipping project…</p>}
    {project && <>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-xl bg-rose-50 p-4 dark:bg-rose-950/30"><div><p role="status" className="text-sm font-semibold">{projectStatus[project.status]}</p><p className="mt-1 text-xs text-gray-500">{formatTime(project.duration)} source · {project.clips.length} clips · Suggested length {project.min_duration}–{project.max_duration}s</p></div>{(project.status === "FAILED" || stale) && <button disabled={working} onClick={() => perform(() => retryClipProject(project.id))} className={editorButton}>Retry processing</button>}</div>
      <button type="button" onClick={load} disabled={working} className="mb-4 min-h-11 text-sm font-semibold text-blue-600 dark:text-blue-300">Refresh progress</button>
      {project.extraction_prompt && <p className="mb-5 rounded-xl border border-gray-200 p-4 text-sm dark:border-gray-700"><span className="font-semibold">Extraction brief: </span>{project.extraction_prompt}</p>}
      {project.error && <p role="alert" className="mb-5 text-sm text-amber-700 dark:text-amber-300">{project.error}</p>}
      {busy && <p className="mb-6 text-sm text-gray-500">You can leave this page and return later. Completed transcription chunks are saved for retries.</p>}
      <FullVideoTranscript key={project.id} title={project.title} words={project.words} />
      {!busy && <div className="mb-5 flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl font-bold">Review your clips</h2><div className="flex w-full flex-wrap gap-3 sm:w-auto"><button disabled={working || !!editing || !selected.length} onClick={() => render(selected)} className={editorButton}>Export selected ({selected.length})</button><button disabled={working || !!editing || project.clips.length >= 20} onClick={add} className="text-sm font-semibold text-blue-600 dark:text-blue-300">+ Add clip manually</button></div></div>}
      {!busy && !project.clips.length && <p className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500 dark:border-gray-700">No suitable highlights were found yet. Add a clip manually and choose its boundaries from the transcript.</p>}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{project.clips.map(clip => <article key={clip.id} className={`rounded-2xl border bg-white p-5 dark:bg-gray-800 ${selected.includes(clip.id) ? "border-rose-400" : "border-gray-200 dark:border-gray-700"}`}><div className="flex items-start gap-3"><input aria-label={`Select ${clip.title}`} type="checkbox" checked={selected.includes(clip.id)} disabled={working || busy || (clipBusy(clip.status) && !clipStalled(clip))} onChange={event => setSelected(current => event.target.checked ? [...current, clip.id] : current.filter(id => id !== clip.id))} className="mt-1 h-5 w-5 shrink-0" /><h3 className="min-w-0 flex-1 break-words font-semibold">{clip.title}</h3></div><p className="mt-3 text-xs text-gray-500">{formatTime(clip.start)}–{formatTime(clip.end)} · {(clip.end - clip.start).toFixed(1)}s</p>{clip.reason && <p className="mt-3 break-words text-sm leading-relaxed text-gray-500 dark:text-gray-400">{clip.reason}</p>}<p className="mt-4 text-xs font-semibold text-rose-600 dark:text-rose-300">{clipBusy(clip.status) && clipStalled(clip) ? "Export stalled · retry available" : clipStatus[clip.status]}</p>{clip.error && <p role="alert" className="mt-2 text-xs text-red-600 dark:text-red-300">{clip.error}</p>}<div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-sm font-semibold [&_button]:min-h-11"><button disabled={working || busy || clipBusy(clip.status) || !!editing} onClick={() => setEditing(clip)} className="text-blue-600 disabled:opacity-40 dark:text-blue-300">Preview & edit</button>{clip.status === "COMPLETED" && <button disabled={working} onClick={() => download(clip)} className="text-emerald-600 dark:text-emerald-300">Download</button>}{(!clipBusy(clip.status) || clipStalled(clip)) && <button disabled={working || busy || !!editing} onClick={() => render([clip.id])} className="text-rose-600 disabled:opacity-40 dark:text-rose-300">{clip.status === "FAILED" || clipStalled(clip) ? "Retry export" : "Export"}</button>}<button disabled={working || busy || clipBusy(clip.status) || !!editing} onClick={async () => { if (await perform(() => deleteClip(project.id, clip.id))) setSelected(current => current.filter(id => id !== clip.id)); }} className="text-gray-400 disabled:opacity-40">Remove</button></div><ClipHashtags projectId={project.id} clip={clip} disabled={busy || !!editing || working} onSaved={load} /></article>)}</div>
      {editing && <ClipEditor key={editing.id} project={project} clip={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />}
      {!busy && !exporting && !editing && <div className="mt-9 border-t border-gray-200 pt-5 text-sm dark:border-gray-700">{deleteMode ? <div className="flex flex-wrap items-center gap-4"><p>Delete this upload and all its clips?</p><button disabled={working} onClick={removeProject} className="font-semibold text-red-600">Delete project</button><button disabled={working} onClick={() => setDeleteMode(false)}>Keep project</button></div> : <button onClick={() => setDeleteMode(true)} className="text-gray-400">Delete clipping project</button>}</div>}
    </>}
  </main>;
}
