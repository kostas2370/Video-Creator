import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { HiOutlineArrowRight, HiOutlinePlus, HiOutlineSparkles, HiOutlineBookOpen } from "react-icons/hi2";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";
import { VideoCreationMode } from "../components/VideoCreationMode";
import { SeriesProfileForm } from "../components/SeriesProfileForm";
import { AssetPagination } from "../components/ui/AssetPagination";
import { editorButton, editorInput } from "../components/ui/EditorDialog";
import { createSeries, getSeries, getSeriesProfile, updateSeries, deleteSeries, getSeriesEpisodes, draftSeriesEpisode, saveEpisodeMemory, retrySeriesEpisode } from "../api/apiService";

const panel = "rounded-2xl border border-gray-200 bg-white p-5 sm:p-6 dark:border-gray-700 dark:bg-gray-800";
const textButton = "rounded-lg px-2 py-2 text-sm font-semibold text-blue-600 disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-300";
const statusNames = { GENERATION: "Preparing episode", REVIEW: "Review storyboard", READY: "Ready to edit", COMPLETED: "Export available", RENDERING: "Exporting", FAILED: "Needs attention" };

export function SeriesHeader() {
  return <header className="mb-8 max-w-2xl"><span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-indigo-600 dark:text-indigo-300"><HiOutlineBookOpen aria-hidden="true" />Series mode</span><h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">A familiar world. A new story.</h1><p className="mt-3 leading-relaxed text-gray-500 dark:text-gray-400">Keep your cast, visual style and narrator together. Give each episode a new idea, with memory of the stories that came before.</p></header>;
}

function SeriesLibrary() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState("");
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true; setLoading(true); setError("");
    getSeries(undefined, page).then(response => {
      if (!active) return;
      if (response.ok) setData(response.data); else setError(response.message);
      setLoading(false);
    });
    return () => { active = false; };
  }, [page, reload]);
  const save = async payload => {
    if (busy) return;
    setBusy(true); setFormError("");
    const response = await createSeries(payload);
    if (response.ok) navigate(`/series/${response.data.id}/`);
    else setFormError(response.message);
    setBusy(false);
  };
  return <>
    <SeriesHeader />
    {creating ? <SeriesProfileForm busy={busy} error={formError} onSave={save} onCancel={() => setCreating(false)} /> : <>
      <div className="mb-5 flex items-center justify-between gap-4"><h2 className="text-xl font-bold">Your series</h2><button type="button" onClick={() => { setFormError(""); setCreating(true); }} className={`${editorButton} inline-flex items-center gap-2`}><HiOutlinePlus aria-hidden="true" />New series</button></div>
      {loading && <p role="status" className="py-8 text-sm text-gray-500">Loading series…</p>}
      {error && <div role="alert" className={panel}><p className="text-red-600 dark:text-red-300">{error}</p><button type="button" onClick={() => setReload(value => value + 1)} className={textButton}>Try again</button></div>}
      {!loading && !error && data?.results?.length === 0 && <div className={`${panel} border-dashed py-12 text-center`}><HiOutlineBookOpen aria-hidden="true" className="mx-auto h-10 w-10 text-indigo-400" /><h3 className="mt-4 text-lg font-semibold">Build a series they recognize</h3><p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-gray-500 dark:text-gray-400">Create a recurring cast, a branded explainer series or a world with a new story every episode. Save your setup, then start episode one.</p><button type="button" onClick={() => setCreating(true)} className={`${textButton} mt-3`}>Create your first series →</button></div>}
      {!loading && !error && <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{data?.results?.map(series => <Link key={series.id} to={`/series/${series.id}/`} className={`${panel} group transition hover:border-indigo-400 focus-visible:ring-2 focus-visible:ring-indigo-500`}><span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600 dark:bg-indigo-950 dark:text-indigo-300">{series.episode_count || 0} episodes</span><h3 className="mt-4 text-lg font-bold">{series.title}</h3><p className="mt-2 line-clamp-3 text-sm leading-relaxed text-gray-500 dark:text-gray-400">{series.premise}</p><span className="mt-5 flex items-center gap-2 text-sm font-semibold text-indigo-600 dark:text-indigo-300">Open series<HiOutlineArrowRight aria-hidden="true" /></span></Link>)}</div>}
      <AssetPagination pagination={data} loading={loading} onPage={setPage} />
    </>}
  </>;
}

export function EpisodeCard({ episode, onMemorySave, onRetry, disabled }) {
  const [memory, setMemory] = useState(episode.summary || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  useEffect(() => { setMemory(episode.summary || ""); }, [episode.summary]);
  const save = async () => {
    if (saving || disabled) return;
    setSaving(true); setError(""); setSaved(false);
    const response = await onMemorySave(episode.id, memory, episode.summary);
    if (!response.ok) setError(response.message); else setSaved(true);
    setSaving(false);
  };
  return <article className={panel}>
    <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><p className="text-xs font-semibold text-indigo-600 dark:text-indigo-300">Episode {episode.number}</p><h3 className="mt-1 break-words font-semibold">{episode.video_title || episode.idea}</h3></div><span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-200">{episode.video_id ? statusNames[episode.status] || "Project saved" : "Video removed · memory kept"}</span></div>
    <p className="mt-3 text-sm leading-relaxed text-gray-500 dark:text-gray-400">{episode.idea}</p>
    <div className="mt-3 flex flex-wrap gap-3">{episode.video_id && <Link to={`/videos/${episode.video_id}/`} className={textButton}>{episode.status === "REVIEW" ? "Review storyboard" : "Open episode"} →</Link>}{episode.can_retry && <button type="button" disabled={disabled} onClick={() => onRetry(episode.id)} className={textButton}>Retry draft</button>}</div>
    <details className="mt-4 border-t border-gray-100 pt-4 dark:border-gray-700"><summary className="cursor-pointer text-sm font-semibold">Episode memory <span className="ml-1 font-normal text-gray-500">{episode.is_canon ? "Used by future episodes" : "Draft"}</span></summary><label className="mt-3 block text-xs leading-relaxed text-gray-500 dark:text-gray-400">Keep the concrete events, discoveries and ending. Review this AI-written memory after changing the story. Future stories use the latest ten memories from episodes whose media is ready.
      <textarea maxLength={800} rows={4} value={memory} disabled={saving || disabled} onChange={event => { setMemory(event.target.value); setSaved(false); }} className={`${editorInput} mt-2`} aria-label={`Memory for episode ${episode.number}`} />
    </label><div className="mt-2 flex items-center justify-between text-xs text-gray-500"><span>{memory.length}/800</span><button type="button" disabled={saving || disabled || memory === episode.summary} onClick={save} className={textButton}>{saving ? "Saving…" : "Save memory"}</button></div>{saved && <p role="status" className="text-xs text-green-700 dark:text-green-300">Episode memory saved.</p>}{error && <p role="alert" className="mt-2 text-sm text-red-600 dark:text-red-300">{error}</p>}</details>
  </article>;
}

function SeriesWorkspace({ id }) {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [episodes, setEpisodes] = useState(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [idea, setIdea] = useState("");
  const [draftError, setDraftError] = useState("");
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true; setLoading(true); setError("");
    Promise.all([getSeriesProfile(id), getSeriesEpisodes(id, page)]).then(([seriesResponse, episodesResponse]) => {
      if (!active) return;
      if (seriesResponse.ok && episodesResponse.ok) { setProfile(seriesResponse.data); setEpisodes(episodesResponse.data); }
      else setError(seriesResponse.message || episodesResponse.message);
      setLoading(false);
    });
    return () => { active = false; };
  }, [id, page, reload]);
  const saveProfile = async payload => {
    if (busy) return;
    setBusy(true); setFormError("");
    const response = await updateSeries(id, payload);
    if (response.ok) { setProfile(response.data); setEditing(false); } else setFormError(response.message);
    setBusy(false);
  };
  const draft = async event => {
    event.preventDefault(); if (busy || editing || !idea.trim()) return;
    setBusy(true); setDraftError("");
    const response = await draftSeriesEpisode(id, idea.trim());
    if (response.ok) navigate(`/videos/${response.data.video_id}/`);
    else { setDraftError(response.message); setReload(value => value + 1); }
    setBusy(false);
  };
  const retry = async episodeId => {
    if (busy) return;
    setBusy(true); setDraftError("");
    const response = await retrySeriesEpisode(id, episodeId);
    if (response.ok) navigate(`/videos/${response.data.video_id}/`); else { setDraftError(response.message); setReload(value => value + 1); }
    setBusy(false);
  };
  const saveMemory = useCallback(async (episodeId, summary, previousSummary) => {
    const response = await saveEpisodeMemory(id, episodeId, summary, previousSummary);
    if (response.ok) setEpisodes(current => ({ ...current, results: current.results.map(row => row.id === episodeId ? response.data : row) }));
    return response;
  }, [id]);
  const remove = async () => {
    if (busy || !window.confirm("Delete this series setup and episode memories? Your videos will remain in My videos.")) return;
    setBusy(true); setFormError("");
    const response = await deleteSeries(id);
    if (response.ok) navigate("/series/"); else setFormError(response.message);
    setBusy(false);
  };
  if (loading && !profile) return <p role="status" className="py-12 text-sm text-gray-500">Loading your series…</p>;
  if (error) return <div className={panel}><p role="alert" className="text-red-600 dark:text-red-300">{error}</p><button type="button" onClick={() => setReload(value => value + 1)} className={textButton}>Try again</button><Link to="/series/" className={textButton}>All series</Link></div>;
  if (!profile) return null;
  const pending = episodes?.results?.some(episode => ["GENERATION", "REVIEW"].includes(episode.status));
  return <>
    <Link to="/series/" className={textButton}>← All series</Link>
    <header className="mb-7 mt-4 flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-widest text-indigo-600 dark:text-indigo-300">Series workspace</p><h1 className="mt-2 break-words text-3xl font-bold">{profile.title}</h1><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{profile.episode_count || 0} episodes · One cast, one style, new stories</p></div><button type="button" disabled={busy} onClick={() => { setEditing(value => !value); setFormError(""); }} className={textButton}>{editing ? "Close setup" : "Edit series setup"}</button></header>
    {editing && <div className="mb-7"><SeriesProfileForm initial={profile} busy={busy} error={formError} onSave={saveProfile} onCancel={() => setEditing(false)} /><div className="mt-3 text-right"><button type="button" disabled={busy} onClick={remove} className="rounded-lg px-3 py-2 text-sm text-red-600 disabled:opacity-40 dark:text-red-300">Delete series</button></div></div>}
    <div className="grid items-start gap-7 lg:grid-cols-[minmax(0,1fr)_300px]">
      <section className="min-w-0"><form onSubmit={draft} className={`${panel} mb-7 border-indigo-200 dark:border-indigo-800`}><h2 className="flex items-center gap-2 text-xl font-bold"><HiOutlineSparkles aria-hidden="true" className="text-indigo-500" />Your next episode</h2><label className="mt-4 block text-sm font-semibold">What happens this time?<textarea required maxLength={2000} rows={4} disabled={busy || editing} value={idea} onChange={event => setIdea(event.target.value)} placeholder="Milo wonders why his shadow gets longer in the evening. He tries an experiment with a lantern…" className={`${editorInput} mt-2`} /></label><p className="mt-3 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Uses your saved setup and the latest ten completed episode memories. You’ll review the storyboard before generating any narration or visuals.</p>{editing && <p role="status" className="mt-3 text-sm text-amber-700 dark:text-amber-300">Save or close series setup before drafting.</p>}{pending && <p role="status" className="mt-3 text-sm text-amber-700 dark:text-amber-300">Finish reviewing and preparing your current episode first.</p>}{draftError && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-300">{draftError}</p>}<button type="submit" disabled={busy || editing || pending || !idea.trim()} className={`${editorButton} mt-5`}>{busy ? "Preparing episode…" : "Draft next episode"}</button><p className="mt-2 text-xs text-gray-500">Drafting uses your AI text provider.</p></form>
        <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">Episodes &amp; memory</h2><button type="button" disabled={loading || busy} onClick={() => setReload(value => value + 1)} className={textButton}>{loading ? "Refreshing…" : "Refresh"}</button></div>
        {episodes?.results?.length === 0 && <div className={`${panel} border-dashed text-sm leading-relaxed text-gray-500 dark:text-gray-400`}>Your series is ready for episode one. Each finished episode adds memory for the next story.</div>}
        <div className="space-y-4">{episodes?.results?.map(episode => <EpisodeCard key={episode.id} episode={episode} onMemorySave={saveMemory} onRetry={retry} disabled={busy || loading} />)}</div><AssetPagination pagination={episodes} loading={loading || busy} onPage={setPage} />
      </section>
      <aside className={`${panel} space-y-5 lg:sticky lg:top-6`}><div><h2 className="font-bold">The series bible</h2><p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-gray-500 dark:text-gray-400">{profile.premise}</p></div>{profile.characters && <div><h3 className="text-xs font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-300">Cast &amp; world</h3><p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-gray-500 dark:text-gray-400">{profile.characters}</p></div>}<div><h3 className="text-xs font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-300">Signature style</h3><p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-gray-500 dark:text-gray-400">{profile.visual_style}</p></div><p className="border-t border-gray-100 pt-4 text-xs leading-relaxed text-gray-500 dark:border-gray-700 dark:text-gray-400">Every episode keeps the setup it started with. Changing the series won’t rewrite earlier videos. Reference images help preserve appearances, but results can vary.</p></aside>
    </div>
  </>;
}

export default function SeriesPage() {
  useAxiosPrivate();
  const { seriesId } = useParams();
  return <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6"><VideoCreationMode />{seriesId ? <SeriesWorkspace key={seriesId} id={seriesId} /> : <SeriesLibrary />}</main>;
}
