import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { HiOutlineBookOpen, HiOutlineSparkles } from "react-icons/hi2";
import { creationModes } from "../utils/creationModes";
import { getNewsUpdates } from "../api/apiService";

const linkStyle = "font-semibold text-blue-600 underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-300";
const panelStyle = "rounded-2xl border border-gray-200 bg-white p-5 sm:p-7 dark:border-gray-700 dark:bg-gray-800";

function HelpLayout({ title, description, children }) {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = `${title} · Viddie`;
    if (!window.location.hash) window.scrollTo(0, 0);
    return () => { document.title = previousTitle; };
  }, [title]);

  return <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
    <Link to="/" className={`text-sm ${linkStyle}`}>← Viddie home</Link>
    <header className="mb-8 mt-7">
      <p className="text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-300">Learn & explore</p>
      <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
      <p className="mt-3 max-w-2xl leading-relaxed text-gray-500 dark:text-gray-400">{description}</p>
      <nav aria-label="Help pages" className="mt-6 flex flex-wrap gap-2">
        {[
          { to: "/guide/", label: "Guide", icon: HiOutlineBookOpen },
          { to: "/whats-new/", label: "What’s new", icon: HiOutlineSparkles },
        ].map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end className={({ isActive }) => `inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${isActive ? "bg-blue-600 text-white" : "bg-white text-gray-600 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"}`}><Icon aria-hidden="true" className="h-4 w-4" />{label}</NavLink>)}
      </nav>
    </header>
    {children}
  </main>;
}

const guideSections = [
  { id: "start", title: "Choose your starting point" },
  { id: "providers", title: "Connect your providers" },
  { id: "edit", title: "Build and edit your scenes" },
  { id: "preview-export", title: "Preview and export" },
  { id: "publish", title: "Publish your video" },
  { id: "clips", title: "Turn a long video into Shorts" },
  { id: "troubleshooting", title: "When something goes wrong" },
];

function GuideSection({ id, title, children }) {
  return <section id={id} aria-labelledby={`${id}-title`} className={`scroll-mt-6 ${panelStyle}`}>
    <h2 id={`${id}-title`} className="text-xl font-bold tracking-tight">{title}</h2>
    <div className="mt-4 space-y-4 text-sm leading-7 text-gray-600 dark:text-gray-300">{children}</div>
  </section>;
}

export function GuidePage() {
  return <HelpLayout title="From your first idea to your final video" description="Choose a creation tool, shape your scenes, and export when you’re ready. Start here whenever you need a hand.">
    <div className="grid items-start gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
      <aside className={`${panelStyle} lg:sticky lg:top-6`}>
        <h2 className="text-sm font-semibold">In this guide</h2>
        <nav aria-label="Guide contents" className="mt-4">
          <ol className="space-y-3 text-sm">{guideSections.map((section, index) => <li key={section.id}><a href={`#${section.id}`} className="flex gap-3 rounded text-gray-500 hover:text-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-gray-400 dark:hover:text-blue-300"><span aria-hidden="true" className="text-blue-600 dark:text-blue-300">0{index + 1}</span>{section.title}</a></li>)}</ol>
        </nav>
      </aside>
      <div className="min-w-0 space-y-5">
        <GuideSection {...guideSections[0]}>
          <p>Open Create and choose the tool that matches what you already have.</p>
          <div className="grid gap-3 sm:grid-cols-2">{creationModes.map(({ to, label, description, requirement, icon: Icon }) => <Link key={to} to={to} className="rounded-xl border border-gray-200 p-4 transition hover:border-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-700">
            <Icon aria-hidden="true" className="mb-3 h-5 w-5 text-blue-600 dark:text-blue-300" /><h3 className="font-semibold text-gray-900 dark:text-white">{label}</h3><p className="mt-1">{description}</p><p className="mt-3 text-xs text-gray-500 dark:text-gray-400">{requirement}</p>
          </Link>)}</div>
        </GuideSection>
        <GuideSection {...guideSections[1]}>
          <p>For AI tools, open <Link to="/api-keys/" className={linkStyle}>API keys and providers</Link> from your account menu. Connect the providers required by your chosen tool before starting. Add captions requires an OpenAI API key.</p>
          <p>You can create a manual project with your own photos, clips, and recorded voiceover without connecting an AI provider.</p>
        </GuideSection>
        <GuideSection {...guideSections[2]}>
          <ol className="list-decimal space-y-3 pl-5">
            <li>For an AI project, review the storyboard’s narration and visual prompts before generating media.</li>
            <li>Open your project from <Link to="/videos/" className={linkStyle}>My videos</Link>. Add scenes, choose their visuals, and arrange them in the order you want.</li>
            <li>Adjust scene timing, transitions, and image motion. Add narration or record a voiceover where needed.</li>
            <li>Use Settings for the output format and appearance, and Project extras for music and other finishing touches.</li>
          </ol>
          <p>Wait for changes to finish saving before previewing or exporting. You can find reusable media in <Link to="/assets/" className={linkStyle}>My assets</Link>.</p>
        </GuideSection>
        <GuideSection {...guideSections[3]}>
          <ol className="list-decimal space-y-3 pl-5">
            <li>Choose <strong>Preview edit</strong> to review your saved scenes. Check their order, framing, narration, captions, and transitions.</li>
            <li>Choose <strong>Export video</strong> and confirm the render. If the app reports missing narration, retry it in the affected scenes or export with the available audio.</li>
            <li>Wait for the export to complete, then choose <strong>Watch export</strong> to review the rendered video.</li>
          </ol>
          <p>The preview shows your current edit; Watch export shows the latest completed render. Export again after making changes to update the rendered video.</p>
        </GuideSection>
        <GuideSection {...guideSections[4]}>
          <p>Open <Link to="/connections/" className={linkStyle}>Connections</Link> from your account menu to connect a supported social account. Available platforms depend on how your workspace is configured.</p>
          <p>After exporting, use the publishing action in the editor to choose an account and review the post details. Reconnect an account if the app says its connection has expired.</p>
        </GuideSection>
        <GuideSection {...guideSections[5]}>
          <p>Open <Link to="/clips/" className={linkStyle}>Long video → Shorts</Link> to find highlights in an interview, podcast, talk, or other video with spoken audio. Transcription needs an OpenAI API key, and AI suggestions use your configured text provider.</p>
          <ol className="list-decimal space-y-3 pl-5">
            <li>Choose <strong>New project</strong>. Upload a video or paste a public YouTube video link, then choose your preferred clip lengths. Optionally describe the moments you want or select a processing range.</li>
            <li>Wait for the preview, transcript, and suggestions. You can leave the page and return to the saved project later.</li>
            <li>Open <strong>Transcript &amp; AI search</strong> to read the transcript or describe another moment to find. Choose <strong>Add and edit clip</strong> on a result to open it in the editor, or use <strong>Add clip manually</strong> from the Clips view.</li>
            <li>Review the context, adjust the trim and portrait framing, and correct the captions. Suggested times can include decimal seconds; keep that precision when editing. Changing the trim rebuilds captions from the source transcript.</li>
            <li>Choose <strong>Save clip</strong>, then export individual clips or use <strong>Export selected</strong>. Download each finished clip. Generate, review, and save hashtags separately if you want them.</li>
          </ol>
          <p>Each project supports up to 20 clips, each at most 180 seconds long. Exports are portrait MP4 files with the original audio. If processing fails, use the available retry action; saved transcription can be reused. Changing a saved clip’s timing, framing, or captions requires a new export.</p>
        </GuideSection>
        <GuideSection {...guideSections[6]}>
          <div className="space-y-3">
            {[
              ["Export is disabled", "Check that the project has scenes and that processing and saving have finished. If processing failed, review the available scenes and the recovery actions shown in the editor."],
              ["Narration is missing", "Use Retry narration in the affected scene. Check that the selected voice provider is connected, or choose to export using the audio already available."],
              ["Processing or rendering failed", "Your project may still contain editable scenes. A failed export does not necessarily mean the scenes are damaged. Check the project’s available actions; if the problem continues, contact support with the project ID and what you were doing."],
              ["The export shows an older edit", "Watch export opens the latest completed render. Save your changes and export again to include them."],
            ].map(([title, text]) => <details key={title} className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"><summary className="cursor-pointer font-semibold text-gray-900 dark:text-white">{title}</summary><p className="mt-3">{text}</p></details>)}
          </div>
          <p>Still stuck? <Link to="/contact/" className={linkStyle}>Contact us</Link> with the project ID and any error message you see.</p>
        </GuideSection>
      </div>
    </div>
  </HelpLayout>;
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
    getNewsUpdates(page).then(response => {
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
    });
    return () => { cancelled = true; };
  }, [page, attempt]);

  return <HelpLayout title="What’s new" description="The latest features, improvements, and announcements from Viddie.">
    <section aria-label="News updates" aria-busy={loading} className="space-y-5">
      {updates.map(update => <article key={update.id} className={panelStyle}>
        <time dateTime={update.published_at} className="text-xs font-semibold text-blue-600 dark:text-blue-300">{new Date(update.published_at).toLocaleDateString(undefined, { dateStyle: "long" })}</time>
        <h2 className="mt-3 text-2xl font-bold tracking-tight">{update.title}</h2>
        <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-gray-600 dark:text-gray-300">{update.content}</p>
      </article>)}
      {loading && <p role="status" className="py-6 text-sm text-gray-500 dark:text-gray-400">Loading updates…</p>}
      {error && <div role="alert" className={panelStyle}><p className="text-sm text-gray-600 dark:text-gray-300">{error}</p><button type="button" onClick={() => setAttempt(value => value + 1)} className={`mt-3 text-sm ${linkStyle}`}>Try again</button></div>}
      {!loading && !error && updates.length === 0 && <div className={panelStyle}><h2 className="text-xl font-bold">No updates yet</h2><p className="mt-3 text-sm text-gray-500 dark:text-gray-400">New features and announcements will appear here when they’re published.</p></div>}
      {hasMore && !error && <button type="button" disabled={loading} onClick={() => setPage(value => value + 1)} className="rounded-xl border border-gray-200 bg-white px-5 py-3 text-sm font-semibold hover:border-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50 dark:border-gray-700 dark:bg-gray-800">Load older updates</button>}
    </section>
    <section className="mt-5 flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-blue-50 p-5 sm:p-7 dark:bg-blue-900/30">
      <div><h2 className="font-bold">New here?</h2><p className="mt-1 text-sm text-gray-600 dark:text-gray-300">Follow the guide from your first project through preview and export.</p></div>
      <Link to="/guide/" className={`text-sm ${linkStyle}`}>Read the guide →</Link>
    </section>
  </HelpLayout>;
}
