import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { HiOutlinePlus, HiOutlineBookOpen } from "react-icons/hi2";
import { EpisodeCard } from "../components/SeriesEpisodeCard";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";
import { EpisodeComposer, SeriesLibraryCard, SeriesOverview } from "../components/SeriesWorkspacePanels";
import { SeriesProfileForm } from "../components/SeriesProfileForm";
import { AssetPagination } from "../components/ui/AssetPagination";
import { editorButton } from "../components/ui/EditorDialog";
import { useDraftOwner } from "../hooks/useCreationDraft";
import { creationDraftKey, readCreationDraft } from "../utils/creationDrafts";
import { createSeries, getSeries, getSeriesProfile, updateSeries, deleteSeries, getSeriesEpisodes, draftSeriesEpisode, saveEpisodeMemory, draftEpisodeMemory, retrySeriesEpisode } from "../api/apiService";

export { EpisodeCard } from "../components/SeriesEpisodeCard";

const panel = "rounded-2xl border border-gray-200 bg-white p-5 sm:p-6 dark:border-gray-700 dark:bg-gray-800";
const textButton = "rounded-lg px-2 py-2 text-sm font-semibold text-blue-600 disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-300";

export function SeriesHeader() {
  return <header className="mb-8 rounded-3xl border border-indigo-100 bg-gradient-to-br from-indigo-50 via-white to-purple-50 p-6 sm:p-9 dark:border-indigo-900 dark:from-indigo-900/40 dark:via-gray-800 dark:to-purple-900/30"><span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-indigo-600 dark:text-indigo-300"><HiOutlineBookOpen aria-hidden="true" />Series mode</span><h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">A familiar world. A new story.</h1><p className="mt-3 max-w-2xl leading-relaxed text-gray-500 dark:text-gray-400">Keep your cast, visual style and narrator together. Give each episode a new idea, with memory of the stories that came before.</p></header>;
}

function SeriesLibrary() {
  const owner = useDraftOwner();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(() => !!readCreationDraft(creationDraftKey(owner, "series-new")));
  const hasDraft = !!readCreationDraft(creationDraftKey(owner, "series-new"));
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
    return response;
  };
  return <>
    {!creating && <SeriesHeader />}
    {creating ? <SeriesProfileForm busy={busy} error={formError} onSave={save} onCancel={() => setCreating(false)} /> : <>
      <div className="mb-5 flex items-center justify-between gap-4"><h2 className="text-xl font-bold">Your series</h2><button type="button" onClick={() => { setFormError(""); setCreating(true); }} className={`${editorButton} inline-flex items-center gap-2`}><HiOutlinePlus aria-hidden="true" />{hasDraft ? "Continue draft" : "New series"}</button></div>
      {loading && <div role="status" aria-label="Loading series" className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{[1, 2, 3].map(item => <div key={item} className="h-72 animate-pulse rounded-2xl bg-gray-100 motion-reduce:animate-none dark:bg-gray-800" />)}</div>}
      {error && <div role="alert" className={panel}><p className="text-red-600 dark:text-red-300">{error}</p><button type="button" onClick={() => setReload(value => value + 1)} className={textButton}>Try again</button></div>}
      {!loading && !error && data?.results?.length === 0 && <div className={`${panel} border-dashed py-12 text-center`}><HiOutlineBookOpen aria-hidden="true" className="mx-auto h-10 w-10 text-indigo-400" /><h3 className="mt-4 text-lg font-semibold">Build a series they recognize</h3><p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-gray-500 dark:text-gray-400">Create a recurring cast, a branded explainer series or a world with a new story every episode. Save your setup, then start episode one.</p><button type="button" onClick={() => setCreating(true)} className={`${textButton} mt-3`}>Create your first series →</button></div>}
      {!loading && !error && <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{data?.results?.map(series => <SeriesLibraryCard key={series.id} series={series} />)}</div>}
      {!loading && <AssetPagination pagination={data} loading={loading} onPage={setPage} />}
    </>}
  </>;
}


function SeriesWorkspace({ id }) {
  const owner = useDraftOwner();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [episodes, setEpisodes] = useState(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(() => !!readCreationDraft(creationDraftKey(owner, `series:${id}`)));
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
    return response;
  };
  const startEpisode = async send => {
    if (busy) return;
    setBusy(true); setDraftError("");
    try {
      const response = await send();
      if (!response.ok) throw new Error(response.message || "Could not prepare the episode.");
      navigate(`/videos/${response.data.video_id}/`);
    } catch (reason) {
      setDraftError(reason.message);
      setReload(value => value + 1);
    } finally { setBusy(false); }
  };
  const draft = event => {
    event.preventDefault();
    if (!editing && !loading && !profile?.active_episode && idea.trim()) startEpisode(() => draftSeriesEpisode(id, idea.trim()));
  };
  const retry = episodeId => startEpisode(() => retrySeriesEpisode(id, episodeId));
  const saveMemory = useCallback(async (episodeId, summary, previousSummary, scriptHash) => {
    const response = await saveEpisodeMemory(id, episodeId, summary, previousSummary, scriptHash);
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
  if (error && !profile) return <div className={panel}><p role="alert" className="text-red-600 dark:text-red-300">{error}</p><button type="button" onClick={() => setReload(value => value + 1)} className={textButton}>Try again</button><Link to="/series/" className={textButton}>All series</Link></div>;
  if (!profile) return null;
  return <>
    <Link to="/series/" className={textButton}>← All series</Link>
    <header className="mb-7 mt-4 flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-widest text-indigo-600 dark:text-indigo-300">Series workspace</p><h1 className="mt-2 break-words text-3xl font-bold">{profile.title}</h1><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{profile.episode_count || 0} episodes · One cast, one style, new stories</p></div><button type="button" disabled={busy} onClick={() => { setEditing(value => !value); setFormError(""); }} className={textButton}>{editing ? "Close setup" : "Edit series setup"}</button></header>
    {error && <div role="alert" className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-200"><p>{error} Your current work is kept.</p><button type="button" disabled={loading} onClick={() => setReload(value => value + 1)} className={textButton}>Try again</button></div>}
    {editing && <div className="mb-7"><SeriesProfileForm initial={profile} busy={busy} error={formError} onSave={saveProfile} onCancel={() => setEditing(false)} /><div className="mt-3 text-right"><button type="button" disabled={busy} onClick={remove} className="rounded-lg px-3 py-2 text-sm text-red-600 disabled:opacity-40 dark:text-red-300">Delete series</button></div></div>}
    <div className="grid items-start gap-7 lg:grid-cols-[minmax(0,1fr)_320px]">
      <section className="min-w-0"><EpisodeComposer profile={profile} idea={idea} onIdeaChange={setIdea} onSubmit={draft} busy={busy} editing={editing} loading={loading} error={draftError} onSetup={() => setEditing(true)} />
        <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">Episodes &amp; memory</h2><button type="button" disabled={loading || busy} onClick={() => setReload(value => value + 1)} className={textButton}>{loading ? "Refreshing…" : "Refresh"}</button></div>
        {episodes?.results?.length === 0 && <div className={`${panel} border-dashed text-sm leading-relaxed text-gray-500 dark:text-gray-400`}>{profile.cast_ready === false ? "Finish your cast setup to begin episode one." : "Your series is ready for episode one."} Each finished episode adds memory for the next story.</div>}
        <div className="space-y-4">{episodes?.results?.map(episode => <EpisodeCard key={episode.id} episode={episode} onMemorySave={saveMemory} onMemoryDraft={(episodeId, summary) => draftEpisodeMemory(id, episodeId, summary)} onRetry={retry} disabled={busy || loading} />)}</div><AssetPagination pagination={episodes} loading={loading || busy} onPage={setPage} />
      </section>
      <SeriesOverview profile={profile} />
    </div>
  </>;
}

export default function SeriesPage() {
  useAxiosPrivate();
  const { seriesId } = useParams();
  return <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{seriesId ? <SeriesWorkspace key={seriesId} id={seriesId} /> : <SeriesLibrary />}</main>;
}
