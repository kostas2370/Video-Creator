import { useEffect, useState } from "react";
import { getVideos } from "../api/apiService";
import { VideoThumbnail } from "../components/VideoThumbnail";
import { videoLibraryInfo } from "../utils/videoLibrary";
import { Link } from "react-router-dom";
import { HiOutlineArrowRight, HiOutlineFilm, HiOutlinePlay, HiOutlineCheck, HiOutlineClock } from "react-icons/hi2";
import { creationModes } from "../utils/creationModes";

function ModePreview({ mode }) {
  return <div aria-hidden="true" className={`relative flex h-40 items-center justify-center overflow-hidden rounded-xl ${mode.background}`}>
    {mode.preview === "clips" && <div className="flex items-center gap-4"><div className="flex h-16 w-28 items-center justify-center rounded-xl bg-rose-200 dark:bg-rose-900"><HiOutlineFilm className="h-7 w-7 text-rose-600 dark:text-rose-200" /></div><mode.icon className="h-6 w-6 text-rose-500" /><div className="flex gap-2">{[1, 2, 3].map(number => <div key={number} className="flex h-24 w-12 items-center justify-center rounded-lg border border-rose-200 bg-white text-sm font-bold text-rose-500 shadow-sm dark:border-rose-800 dark:bg-gray-900">0{number}</div>)}</div></div>}
    {mode.preview === "series" && <div className="w-4/5 max-w-64"><div className="mb-3 flex items-center gap-2 text-xs font-semibold text-indigo-700 dark:text-indigo-200"><mode.icon className="h-4 w-4" />Same world. New adventures.</div><div className="flex gap-2">{[1, 2, 3].map(number => <div key={number} className={`flex aspect-[3/4] flex-1 flex-col items-center justify-center rounded-xl border border-indigo-200 bg-white shadow-sm dark:border-indigo-800 dark:bg-gray-900 ${number === 2 ? "-translate-y-1" : ""}`}><span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 dark:bg-indigo-900 dark:text-indigo-200">✦</span><span className="mt-3 text-[10px] font-bold text-indigo-600 dark:text-indigo-200">EPISODE {number}</span></div>)}</div></div>}
    {mode.preview === "ai" && <div className="w-4/5 max-w-64 -rotate-3 rounded-xl border border-blue-200 bg-white p-4 shadow-sm dark:border-blue-800 dark:bg-gray-900"><div className="mb-3 flex items-center gap-2 text-xs font-semibold text-blue-600 dark:text-blue-300"><mode.icon className="h-4 w-4" />An idea becomes a story</div><div className="grid grid-cols-3 gap-2">{["bg-blue-100 dark:bg-blue-900", "bg-indigo-100 dark:bg-indigo-900", "bg-sky-100 dark:bg-sky-900"].map((color, i) => <div key={color} className={`flex h-14 items-center justify-center rounded-lg ${color}`}><span className="text-xs font-semibold text-blue-700 dark:text-blue-200">0{i + 1}</span></div>)}</div></div>}
    {mode.preview === "story" && <div className="relative flex h-32 w-24 -rotate-6 items-center justify-center rounded-2xl border-4 border-gray-800 bg-gradient-to-br from-violet-600 to-indigo-950 shadow-lg"><HiOutlinePlay className="h-8 w-8 text-white/30" /><span className="absolute inset-x-1 bottom-5 text-center text-xs font-black leading-tight text-white">THEN <span className="text-yellow-300">EVERYTHING</span><br />CHANGED.</span><span className="absolute -right-20 top-8 rounded-lg bg-white px-3 py-2 text-xs font-semibold text-violet-700 shadow-sm dark:bg-gray-800 dark:text-violet-200">Your story. Your voice.</span></div>}
    {mode.preview === "manual" && <div className="w-4/5 max-w-64 rotate-2 rounded-xl border border-emerald-200 bg-white p-4 shadow-sm dark:border-emerald-800 dark:bg-gray-900"><div className="mb-3 flex items-center gap-2 text-xs font-semibold text-emerald-700 dark:text-emerald-300"><HiOutlineFilm className="h-4 w-4" />Make it yours</div><div className="flex gap-1.5">{["bg-emerald-200 dark:bg-emerald-800", "bg-teal-200 dark:bg-teal-800", "bg-green-200 dark:bg-green-800"].map(color => <div key={color} className={`h-9 flex-1 rounded ${color}`} />)}</div><div className="mt-2 h-3 rounded bg-emerald-100 dark:bg-emerald-900" /><div className="mt-1.5 h-2 w-2/3 rounded bg-teal-100 dark:bg-teal-900" /></div>}
    {mode.preview === "captions" && <div className="text-center"><p className="text-2xl font-black tracking-tight text-gray-900 dark:text-white">EVERY WORD.<br /><span className="rounded bg-amber-300 px-2 text-gray-950">RIGHT ON TIME.</span></p><div className="mt-4 flex justify-center gap-1">{[3, 6, 4, 8, 5, 9, 4, 6, 3, 7, 5, 3, 6, 4, 7].map((height, i) => <span key={i} style={{ height: height * 2 }} className="w-1 self-center rounded-full bg-amber-400 dark:bg-amber-500" />)}</div></div>}
  </div>;
}

function RecentProjects() {
  const [state, setState] = useState({ loading: true, videos: [], error: false });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setState(previous => ({ ...previous, loading: true, error: false }));
    getVideos("", 1, "", { ordering: "-updated_at" }).then(result => {
      if (!active) return;
      const videos = result.ok && Array.isArray(result.data?.results) ? result.data.results.slice(0, 3) : null;
      setState({ loading: false, videos: videos || [], error: !videos });
    }).catch(() => {
      if (active) setState({ loading: false, videos: [], error: true });
    });
    return () => { active = false; };
  }, [attempt]);

  return <section aria-labelledby="recent-heading" className="mb-10">
    <div className="mb-4 flex items-center justify-between gap-3">
      <h2 id="recent-heading" className="flex items-center gap-2 text-base font-semibold"><HiOutlineClock aria-hidden="true" className="h-4 w-4 text-gray-400" />Pick up where you left off</h2>
      <Link to="/videos/" className="studio-text-link shrink-0">All videos <HiOutlineArrowRight aria-hidden="true" className="h-4 w-4" /></Link>
    </div>
    {state.loading ? <div role="status" className="grid gap-4 md:grid-cols-3"><span className="sr-only">Loading recent projects</span>{[1, 2, 3].map(item => <div key={item} className="studio-panel flex items-center gap-4 p-3"><div className="h-20 w-28 shrink-0 rounded-xl bg-gray-100 motion-safe:animate-pulse dark:bg-gray-700" /><div className="flex-1 space-y-3"><div className="h-3 w-3/4 rounded bg-gray-100 dark:bg-gray-700" /><div className="h-3 w-1/2 rounded bg-gray-100 dark:bg-gray-700" /></div></div>)}</div>
      : state.error ? <div role="alert" className="studio-panel flex flex-wrap items-center justify-between gap-3 p-5"><p className="text-sm text-gray-500 dark:text-gray-400">We couldn’t load your recent projects.</p><button type="button" onClick={() => setAttempt(value => value + 1)} className="studio-text-link">Try again</button></div>
      : state.videos.length ? <div className="grid gap-4 md:grid-cols-3">{state.videos.map(video => {
        const info = videoLibraryInfo(video);
        return <article key={video.id} className="studio-panel group flex min-w-0 items-center gap-3 p-3">
          <VideoThumbnail video={video} compact />
          <div className="min-w-0 flex-1"><p className={`mb-1.5 inline-block rounded-md px-2 py-0.5 text-[10px] font-semibold ${info.color}`}>{info.label}</p><h3 className="truncate text-sm font-semibold" title={video.title || "Untitled video"}>{video.title || "Untitled video"}</h3><Link to={`/videos/${video.id}/`} aria-label={`Continue editing ${video.title || "Untitled video"}`} className="studio-text-link mt-2 text-xs">Continue editing<HiOutlineArrowRight aria-hidden="true" className="h-3 w-3" /></Link></div>
        </article>;
      })}</div>
      : <div className="studio-panel flex items-center gap-4 border-dashed p-5"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-300"><HiOutlineFilm aria-hidden="true" className="h-5 w-5" /></span><div><h3 className="text-sm font-semibold">A little empty. Full of possibilities.</h3><p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Start a video below. Your recent projects will appear here.</p></div></div>}
  </section>;
}

export default function CreatePage() {
  const featured = ["ai", "manual"].map(preview => creationModes.find(mode => mode.preview === preview));
  const moreTools = creationModes.filter(mode => !["ai", "manual"].includes(mode.preview));
  return <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:py-10">
    <header className="mb-8 flex flex-wrap items-end justify-between gap-5">
      <div><p className="studio-eyebrow mb-2">Your creative workspace</p><h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Let’s make something worth watching.</h1><p className="mt-3 text-sm leading-relaxed text-gray-500 sm:text-base dark:text-gray-400">A new idea or your own footage. Every great video starts somewhere.</p></div>
    </header>
    <RecentProjects />
    <section aria-labelledby="start-heading">
      <div className="mb-4"><h2 id="start-heading" className="text-lg font-semibold tracking-tight">Start a new video</h2><p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Choose how you’d like to begin.</p></div>
      <div className="grid gap-5 md:grid-cols-2">{featured.map(mode => <Link key={mode.to} to={mode.to} className="studio-panel studio-card group flex min-w-0 flex-col overflow-hidden p-5 sm:p-6">
        <div className="mb-5 flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-300"><mode.icon aria-hidden="true" className="h-5 w-5" /></span><span className="studio-eyebrow">{mode.eyebrow}</span></div>
        <h3 className="text-2xl font-semibold tracking-tight">{mode.label}</h3><p className="mb-5 mt-2 max-w-md text-sm leading-relaxed text-gray-500 dark:text-gray-400">{mode.description}</p>
        <ModePreview mode={mode} />
        <p className="mb-5 mt-4 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400"><HiOutlineCheck aria-hidden="true" className="h-4 w-4 shrink-0 text-blue-500" />{mode.requirement}</p>
        <span className={`${mode.preview === "ai" ? "studio-primary-button" : "studio-secondary-button"} mt-auto w-full justify-between`}>{mode.action}<HiOutlineArrowRight aria-hidden="true" className="h-4 w-4 transition-transform motion-safe:group-hover:translate-x-1" /></span>
      </Link>)}</div>
    </section>
    <section aria-labelledby="tools-heading" className="mt-9">
      <div className="mb-4"><h2 id="tools-heading" className="text-lg font-semibold tracking-tight">More ways to create</h2><p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Have a specific result in mind? Start here.</p></div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{moreTools.map(mode => <Link key={mode.to} to={mode.to} className="studio-panel studio-card group flex min-w-0 flex-col p-4">
        <div className="tool-preview mb-4"><ModePreview mode={mode} /></div>
        <h3 className="text-sm font-semibold">{mode.label}</h3><p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">{mode.description}</p><p className="mb-4 mt-3 text-[11px] leading-relaxed text-gray-500 dark:text-gray-400">{mode.requirement}</p><span className="studio-text-link mt-auto justify-between border-t border-gray-100 pt-3 text-xs dark:border-gray-700">{mode.action}<HiOutlineArrowRight aria-hidden="true" className="h-4 w-4" /></span>
      </Link>)}</div>
    </section>
    <footer className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-gray-200 pt-5 text-xs leading-relaxed text-gray-500 dark:border-gray-800 dark:text-gray-400"><p>Your media, your pace. Connect providers when you want a little AI help.</p><Link to="/api-keys/" className="studio-text-link">Manage providers<HiOutlineArrowRight aria-hidden="true" className="h-3 w-3" /></Link></footer>
  </main>;
}
