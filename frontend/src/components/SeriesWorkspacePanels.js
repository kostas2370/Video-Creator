import { Link } from "react-router-dom";
import { HiOutlineArrowRight, HiOutlineBookOpen, HiOutlineSparkles } from "react-icons/hi2";
import { videoFormats } from "../utils/videoFormats";
import { visualProviderNames } from "../utils/visualProviders";
import { API_HOST } from "../endpoints";
import { editorButton, editorInput } from "./ui/EditorDialog";

const surface = "rounded-2xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800";
const seriesReferenceUrl = image => image && (/^https?:\/\//i.test(image) ? image : `${API_HOST}${image}`);

export function SeriesLibraryCard({ series }) {
  const frame = videoFormats.find(item => item.value === series.video_format);
  return <Link to={`/series/${series.id}/`} className={`${surface} group flex flex-col overflow-hidden transition hover:-translate-y-1 hover:border-indigo-400 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500`}>
    <div className="relative flex h-36 items-center justify-center overflow-hidden bg-gradient-to-br from-indigo-100 via-purple-50 to-blue-100 dark:from-indigo-900 dark:via-gray-800 dark:to-blue-900">
      {series.reference_image ? <img src={seriesReferenceUrl(series.reference_image)} alt="" loading="lazy" className="h-full w-full object-cover transition duration-300 group-hover:scale-105" /> : <HiOutlineBookOpen aria-hidden="true" className="h-12 w-12 text-indigo-400 dark:text-indigo-300" />}
      <span className="absolute bottom-3 left-3 rounded-full bg-white/95 px-3 py-1 text-xs font-semibold text-gray-800 shadow-sm dark:bg-gray-900/95 dark:text-gray-100">{series.episode_count || 0} episodes</span>
    </div>
    <div className="flex flex-1 flex-col p-5"><h3 className="break-words text-lg font-bold">{series.title}</h3><p className="mt-2 line-clamp-2 text-sm leading-relaxed text-gray-500 dark:text-gray-400">{series.premise}</p>
      <div className="mt-4 flex flex-wrap gap-2 text-xs text-gray-500 dark:text-gray-400">{frame && <span>{frame.label} · {frame.ratio}</span>}{series.scene_count && <span>· {series.scene_count} shots</span>}</div>
      <span className="mt-5 flex items-center justify-between gap-2 border-t border-gray-100 pt-4 text-sm font-semibold text-indigo-600 dark:border-gray-700 dark:text-indigo-300">{series.active_episode ? `Continue episode ${series.active_episode.number}` : "Open series"}<HiOutlineArrowRight aria-hidden="true" /></span>
    </div>
  </Link>;
}

export function EpisodeComposer({ profile, idea, onIdeaChange, onSubmit, busy, editing, loading, error }) {
  const active = profile.active_episode;
  if (active) return <section aria-label="Current episode" className="mb-7 rounded-2xl border border-indigo-200 bg-indigo-50 p-5 sm:p-6 dark:border-indigo-800 dark:bg-indigo-900/40">
    <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-300">Pick up where you left off</span>
    <h2 className="mt-2 text-2xl font-bold">Episode {active.number} is in progress</h2>
    <p className="mt-2 max-w-xl text-sm leading-relaxed text-gray-600 dark:text-gray-300">Open your episode to review the storyboard or follow its progress. Once its media is ready, you can start the next story.</p>
    <Link to={`/videos/${active.video_id}/`} className={`${editorButton} mt-5 inline-flex items-center gap-2`}>Continue episode {active.number}<HiOutlineArrowRight aria-hidden="true" /></Link>
    {error && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-300">{error}</p>}
  </section>;
  return <form onSubmit={onSubmit} className={`${surface} mb-7 overflow-hidden`} aria-label="Draft next episode">
    <div className="border-b border-gray-100 bg-gradient-to-r from-indigo-50 to-white px-5 py-4 sm:px-6 dark:border-gray-700 dark:from-indigo-900/50 dark:to-gray-800">
      <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-300"><HiOutlineSparkles aria-hidden="true" />Next chapter</span>
      <h2 className="mt-2 text-2xl font-bold">{profile.episode_count ? "What happens next?" : "Let’s make episode one"}</h2>
      <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Your cast and style are saved. All you need is a new idea.</p>
    </div>
    <div className="p-5 sm:p-6">
      <label className="block text-sm font-semibold">Episode idea<textarea required maxLength={2000} rows={3} disabled={busy || editing || loading} value={idea} onChange={event => onIdeaChange(event.target.value)} placeholder="A new question, a surprising discovery, or a problem for your characters to solve…" className={`${editorInput} mt-2 resize-y font-normal`} /></label>
      <div className="mt-2 flex items-center justify-between gap-3 text-xs text-gray-500 dark:text-gray-400"><span>A specific starting point makes a stronger story.</span><span className="shrink-0">{idea.length}/2000</span></div>
      <ol aria-label="Episode creation steps" className="my-4 grid grid-cols-3 gap-2 border-y border-gray-100 py-3 text-xs dark:border-gray-700">{["Add an idea", "Review storyboard", "Generate media"].map((step, index) => <li key={step} className="flex items-center gap-2"><span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full font-semibold ${index === 0 ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-200" : "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-300"}`}>{index + 1}</span><span>{step}</span></li>)}</ol>
      {editing && <p role="status" className="mb-3 text-sm text-amber-700 dark:text-amber-300">Save or close series setup before drafting.</p>}
      {error && <p role="alert" className="mb-3 text-sm text-red-600 dark:text-red-300">{error}</p>}
      <div className="flex flex-wrap items-center gap-3"><button type="submit" disabled={busy || editing || loading || !idea.trim()} className={`${editorButton} inline-flex items-center gap-2`}><HiOutlineSparkles aria-hidden="true" />{busy ? "Preparing episode…" : "Draft next episode"}</button><span className="text-xs text-gray-500 dark:text-gray-400">Review the script before generating media.</span></div>
      <p className="mt-3 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Uses your AI text provider, saved setup and reviewed memories from the latest ten prepared episodes.</p>
    </div>
  </form>;
}

export function SeriesOverview({ profile }) {
  const frame = videoFormats.find(item => item.value === profile.video_format);
  return <aside className={`${surface} min-w-0 overflow-hidden lg:sticky lg:top-6`} aria-label="Saved series setup">
    <div className="border-b border-gray-100 p-5 dark:border-gray-700"><h2 className="flex items-center gap-2 font-bold"><HiOutlineBookOpen aria-hidden="true" className="text-indigo-500" />Series setup</h2><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Carried into every new episode</p></div>
    {profile.reference_image && <img src={seriesReferenceUrl(profile.reference_image)} alt="Saved cast and style reference" className="max-h-52 w-full bg-gray-50 object-contain dark:bg-gray-900" />}
    <div className="space-y-5 p-5">
      <dl className="grid grid-cols-2 gap-4 text-sm"><div><dt className="text-xs text-gray-500 dark:text-gray-400">Frame</dt><dd className="mt-1 font-semibold">{frame ? `${frame.label} ${frame.ratio}` : profile.video_format}</dd></div><div><dt className="text-xs text-gray-500 dark:text-gray-400">Episode length</dt><dd className="mt-1 font-semibold">{profile.scene_count} shots</dd></div><div><dt className="text-xs text-gray-500 dark:text-gray-400">Narration</dt><dd className="mt-1 font-semibold">{profile.narration ? "Saved narrator" : "No narration"}</dd></div><div><dt className="text-xs text-gray-500 dark:text-gray-400">Captions</dt><dd className="mt-1 font-semibold">{profile.subtitles ? "On" : "Off"}</dd></div></dl>
      <p className="text-xs text-gray-500 dark:text-gray-400">{visualProviderNames[profile.provider] || profile.provider}</p>
      <details className="border-t border-gray-100 pt-4 dark:border-gray-700"><summary className="cursor-pointer text-sm font-semibold">World, cast &amp; style</summary><div className="mt-4 space-y-4">{[["Premise", profile.premise], ["Cast & world", profile.characters], ["Signature style", profile.visual_style]].filter(([, value]) => value).map(([label, value]) => <div key={label}><h3 className="text-xs font-semibold text-indigo-600 dark:text-indigo-300">{label}</h3><p className="mt-1 whitespace-pre-line break-words text-sm leading-relaxed text-gray-500 dark:text-gray-400">{value}</p></div>)}</div></details>
      <p className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">Setup changes apply to future episodes. Each existing episode keeps its original choices. References guide appearance; results can vary.</p>
    </div>
  </aside>;
}
