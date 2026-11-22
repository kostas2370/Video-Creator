import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { HiOutlineArrowRight, HiOutlineBookOpen, HiOutlineSparkles } from "react-icons/hi2";
import { creationModes } from "../utils/creationModes";
import { getNewsUpdates } from "../api/apiService";
import { HelpLayout, linkStyle, panelStyle } from "../components/help/HelpLayout";

function NewsEntry({ update, latest }) {
  const date = new Date(update.published_at);
  return <article className="relative grid min-w-0 gap-3 pl-6 sm:grid-cols-[70px_minmax(0,1fr)] sm:gap-5 sm:pl-8">
    <span aria-hidden="true" className={`absolute -left-[5px] top-3 h-2.5 w-2.5 rounded-full ring-4 ring-gray-50 dark:ring-gray-900 ${latest ? "bg-blue-500" : "bg-gray-300 dark:bg-gray-600"}`} />
    <time dateTime={update.published_at} className="pt-1 text-xs font-medium text-gray-500 dark:text-gray-400"><span className="sm:block sm:text-2xl sm:font-semibold sm:tracking-tight sm:text-gray-700 sm:dark:text-gray-200">{date.toLocaleDateString(undefined, { day: "numeric" })}</span><span className="ml-1 sm:ml-0">{date.toLocaleDateString(undefined, { month: "short", year: "numeric" })}</span></time>
    <div className={`min-w-0 overflow-hidden rounded-2xl border ${latest ? "border-blue-200 bg-white dark:border-blue-800 dark:bg-gray-800" : "border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"}`}>
      {latest && <div className="flex items-center justify-between gap-4 border-b border-blue-100 bg-blue-50 px-5 py-3 text-blue-700 sm:px-7 dark:border-blue-900 dark:bg-blue-900/30 dark:text-blue-300"><span className="flex items-center gap-2 text-xs font-semibold"><HiOutlineSparkles aria-hidden="true" className="h-4 w-4" />Latest update</span><span className="text-xs">Fresh from Viddie</span></div>}
      <div className="p-5 sm:p-7"><p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400">Product update</p><h3 className={`break-words font-bold leading-snug tracking-tight ${latest ? "text-2xl sm:text-3xl" : "text-xl sm:text-2xl"}`}>{update.title}</h3>
        <div className="mt-5 space-y-4 text-sm leading-7 text-gray-600 dark:text-gray-300">{update.content.split(/\n\s*\n/).map((paragraph, paragraphIndex) => <p key={paragraphIndex} className="whitespace-pre-wrap break-words">{paragraph}</p>)}</div>
      </div>
    </div>
  </article>;
}

export function WhatsNewPage() {
  const [updates, setUpdates] = useState([]);
  const [page, setPage] = useState(1);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    async function loadUpdates() {
      let response;
      try {
        response = await getNewsUpdates(page);
      } catch {
        response = { ok: false };
      }
      if (cancelled) return;
      if (response.ok) {
        setUpdates(current => page === 1 ? response.data.results : [
          ...current,
          ...response.data.results.filter(update => !current.some(row => row.id === update.id)),
        ]);
        setHasMore(Boolean(response.data.next));
      } else {
        setError("Could not load news updates. Please try again.");
      }
      setLoading(false);
    }
    loadUpdates();
    return () => { cancelled = true; };
  }, [page, attempt]);

  return <HelpLayout title="Small changes. More possibilities." eyebrow="What’s new at Viddie" description="New tools, thoughtful improvements, and more ways to turn your ideas into videos. Follow along as Viddie grows.">
    <div className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 pb-5 dark:border-gray-700"><div><h2 className="text-lg font-bold">The release journal</h2><p className="mt-1 text-sm text-gray-500 dark:text-gray-400">What changed, why it helps, and where to start.</p></div><a href="#release-updates" className={`inline-flex items-center gap-2 text-sm ${linkStyle}`}>Browse updates<HiOutlineArrowRight aria-hidden="true" className="h-4 w-4" /></a></div>
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_260px]">
    <section id="release-updates" aria-label="News updates" aria-busy={loading} className="min-w-0 scroll-mt-6 space-y-6">
      <div className={updates.length ? "ml-1 space-y-6 border-l border-gray-200 dark:border-gray-700" : ""}>
        {updates.map((update, index) => {
          const month = new Date(update.published_at).toLocaleDateString(undefined, { month: "long", year: "numeric" });
          const previousMonth = index > 0 && new Date(updates[index - 1].published_at).toLocaleDateString(undefined, { month: "long", year: "numeric" });
          return <div key={update.id} className="space-y-4">{month !== previousMonth && <h2 className="pl-6 text-xs font-semibold uppercase tracking-widest text-gray-500 sm:pl-8 dark:text-gray-400">{month}</h2>}<NewsEntry update={update} latest={index === 0} /></div>;
        })}
      </div>
      {loading && <p role="status" className="py-6 text-sm text-gray-500 dark:text-gray-400">Loading updates…</p>}
      {error && <div role="alert" className={panelStyle}><p className="text-sm text-gray-600 dark:text-gray-300">{error}</p><button type="button" onClick={() => setAttempt(value => value + 1)} className={`mt-3 text-sm ${linkStyle}`}>Try again</button></div>}
      {!loading && !error && updates.length === 0 && <div className={panelStyle}><h2 className="text-xl font-bold">No updates yet</h2><p className="mt-3 text-sm text-gray-500 dark:text-gray-400">New features and announcements will appear here when they’re published.</p></div>}
      {hasMore && !error && <button type="button" disabled={loading} onClick={() => setPage(value => value + 1)} className="rounded-xl border border-gray-200 bg-white px-5 py-3 text-sm font-semibold hover:border-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50 dark:border-gray-700 dark:bg-gray-800">{loading ? "Loading older updates…" : "Load older updates"}</button>}
    </section>
    <aside aria-label="Explore Viddie" className="space-y-4 lg:sticky lg:top-6">
      <section className={panelStyle}><p className="text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-300">Make something next</p><h2 className="mt-3 font-bold">Your next video starts here</h2><nav aria-label="Try a creation tool" className="mt-4 space-y-2">{creationModes.filter(mode => ["/ai/", "/clips/", "/manual/"].includes(mode.to)).map(({ to, label, icon: Icon }) => <Link key={to} to={to} className="flex items-center gap-3 rounded-xl border border-gray-200 px-3 py-3 text-sm font-medium transition hover:border-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-700"><Icon aria-hidden="true" className="h-4 w-4 shrink-0 text-blue-500" /><span>{label}</span><HiOutlineArrowRight aria-hidden="true" className="ml-auto h-3.5 w-3.5 shrink-0 text-gray-400" /></Link>)}</nav></section>
      <section className="rounded-2xl bg-blue-50 p-5 sm:p-7 dark:bg-blue-900/30"><HiOutlineBookOpen aria-hidden="true" className="mb-4 h-6 w-6 text-blue-600 dark:text-blue-300" /><h2 className="font-bold">Put an update to work</h2><p className="mb-4 mt-2 text-sm leading-6 text-gray-600 dark:text-gray-300">The guide takes you from choosing a tool to sharing your finished video.</p><Link to="/guide/" className={`text-sm ${linkStyle}`}>Explore the guide →</Link></section>
      <section className={panelStyle}><h2 className="font-bold">Help shape Viddie</h2><p className="mb-4 mt-2 text-sm leading-6 text-gray-500 dark:text-gray-400">Found a problem or missing something? Tell us what you were trying to create.</p><Link to="/contact/" className={`text-sm ${linkStyle}`}>Send feedback →</Link></section>
    </aside>
    </div>
  </HelpLayout>;
}
