import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  HiOutlineArrowRight,
  HiOutlineBookOpen,
  HiOutlineFilm,
  HiOutlineMagnifyingGlass,
  HiOutlineScissors,
  HiOutlineSparkles,
} from "react-icons/hi2";
import {
  HelpLayout,
  linkStyle,
  panelStyle,
} from "../components/help/HelpLayout";
import { guideProblems, guideTopics } from "../content/guide";

const groups = [...new Set(guideTopics.map((topic) => topic.group))];
const startingPoints = [
  {
    id: "start",
    label: "I have photos or clips",
    detail: "Make a first video without API keys.",
    icon: HiOutlineFilm,
  },
  {
    id: "ai",
    label: "I have an idea",
    detail: "Plan and prepare scenes with AI.",
    icon: HiOutlineSparkles,
  },
  {
    id: "clips",
    label: "I have a long video",
    detail: "Find a moment worth sharing.",
    icon: HiOutlineScissors,
  },
];

function EditorMap() {
  return (
    <figure className="overflow-hidden rounded-2xl border border-gray-200 dark:border-gray-700">
      <figcaption className="border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-semibold dark:border-gray-700 dark:bg-gray-900/50">
        Editor map · simplified layout
      </figcaption>
      <div className="grid gap-4 p-4 sm:grid-cols-[1fr_1.2fr]">
        <div className="flex min-h-32 items-center justify-center rounded-xl bg-blue-50 p-5 text-center text-sm font-medium text-blue-700 dark:bg-blue-500/10 dark:text-blue-300">
          Scene preview
          <br />
          Check the picture and sound
        </div>
        <div>
          <p className="mb-2 text-xs font-semibold text-gray-500 dark:text-gray-400">
            Scene controls
          </p>
          <ul className="flex flex-wrap gap-2">
            {["Script", "Visual", "Audio", "Captions", "Timing"].map(
              (label) => (
                <li
                  key={label}
                  className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium dark:border-gray-700"
                >
                  {label}
                </li>
              ),
            )}
          </ul>
          <p className="mt-3 text-xs leading-5 text-gray-500 dark:text-gray-400">
            Select a tab to change that part of the current scene.
          </p>
        </div>
        <div className="rounded-xl bg-gray-50 p-3 sm:col-span-2 dark:bg-gray-900/50">
          <p className="mb-2 text-xs font-semibold">Storyboard</p>
          <ol className="flex gap-2">
            {[1, 2, 3].map((number) => (
              <li
                key={number}
                className="rounded-lg border border-gray-200 bg-white px-5 py-3 text-xs dark:border-gray-700 dark:bg-gray-800"
              >
                Scene {number}
              </li>
            ))}
          </ol>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Select a scene here. Reorder it to change the sequence.
          </p>
        </div>
      </div>
    </figure>
  );
}

export default function GuidePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const heading = useRef(null);
  const [query, setQuery] = useState("");
  const topic =
    guideTopics.find((item) => item.id === location.hash.slice(1)) ||
    guideTopics[0];
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const results = guideTopics.filter((item) => {
    const text = [
      item.title,
      item.description,
      item.needs,
      item.result,
      item.tip,
      ...item.steps.flat(),
      ...(item.id === "troubleshooting" ? guideProblems.flat() : []),
    ]
      .join(" ")
      .toLowerCase();
    return words.every((word) => text.includes(word));
  });

  useEffect(() => {
    if (location.hash && heading.current) {
      heading.current.focus({ preventScroll: true });
      heading.current.scrollIntoView({ block: "start", behavior: "instant" });
    }
  }, [location.key, location.hash]);

  const topicLink = (id) => `/guide/#${id}`;
  return (
    <HelpLayout
      title="Your next video, step by step"
      description="Pick what you want to make. Get the setup, the exact steps, and a clear next move."
      eyebrow="The Viddie guide"
    >
      <section aria-labelledby="guide-start-heading" className="mb-8">
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="guide-start-heading" className="text-lg font-bold">
            New here? Start with what you have.
          </h2>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Three ways to make a first project
          </span>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          {startingPoints.map(({ id, label, detail, icon: Icon }) => (
            <Link
              key={id}
              to={topicLink(id)}
              onClick={() => setQuery("")}
              className={`${panelStyle} group !p-5 transition hover:border-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500`}
            >
              <Icon
                aria-hidden="true"
                className="mb-4 h-6 w-6 text-blue-600 dark:text-blue-300"
              />
              <span className="flex items-center justify-between gap-2 text-sm font-bold">
                {label}
                <HiOutlineArrowRight
                  aria-hidden="true"
                  className="h-4 w-4 shrink-0 text-blue-500"
                />
              </span>
              <span className="mt-2 block text-xs leading-5 text-gray-500 dark:text-gray-400">
                {detail}
              </span>
            </Link>
          ))}
        </div>
      </section>
      <div className="grid items-start gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside
          className={`${panelStyle} !p-4 lg:sticky lg:top-6 lg:max-h-[calc(100dvh-3rem)] lg:overflow-y-auto`}
        >
          <label
            htmlFor="guide-topic"
            className="mb-2 block text-sm font-semibold lg:hidden"
          >
            Choose a guide
          </label>
          <select
            id="guide-topic"
            value={topic.id}
            onChange={(event) => {
              setQuery("");
              navigate(topicLink(event.target.value));
            }}
            className="w-full min-w-0 rounded-xl border border-gray-300 bg-transparent px-3 py-3 text-sm focus:ring-2 focus:ring-blue-500 lg:hidden dark:border-gray-600 dark:bg-gray-800"
          >
            {groups.map((group) => (
              <optgroup key={group} label={group}>
                {guideTopics
                  .filter((item) => item.group === group)
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.title}
                    </option>
                  ))}
              </optgroup>
            ))}
          </select>
          <nav
            aria-label="Guide contents"
            className="hidden space-y-5 lg:block"
          >
            {groups.map((group) => (
              <div key={group}>
                <h2 className="mb-2 px-2 text-[10px] font-bold uppercase tracking-widest text-gray-500 dark:text-gray-400">
                  {group}
                </h2>
                <ul className="space-y-1">
                  {guideTopics
                    .filter((item) => item.group === group)
                    .map((item) => (
                      <li key={item.id}>
                        <Link
                          to={topicLink(item.id)}
                          onClick={() => setQuery("")}
                          aria-current={
                            item.id === topic.id && !words.length
                              ? "page"
                              : undefined
                          }
                          className={`block rounded-lg px-3 py-2.5 text-xs leading-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${item.id === topic.id && !words.length ? "bg-blue-50 font-semibold text-blue-700 dark:bg-blue-500/10 dark:text-blue-300" : "text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-700/50"}`}
                        >
                          {item.title}
                        </Link>
                      </li>
                    ))}
                </ul>
              </div>
            ))}
          </nav>
        </aside>
        <div className="min-w-0">
          <label
            htmlFor="guide-search"
            className="mb-2 block text-sm font-semibold"
          >
            Search the guide
          </label>
          <div className="relative mb-5">
            <HiOutlineMagnifyingGlass
              aria-hidden="true"
              className="pointer-events-none absolute left-4 top-4 h-5 w-5 text-gray-400"
            />
            <input
              id="guide-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Try missing audio, export, or API keys"
              className="w-full min-w-0 rounded-2xl border border-gray-300 bg-white py-3.5 pl-12 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800"
            />
          </div>
          {words.length > 0 ? (
            <section
              aria-labelledby="guide-search-heading"
              className={panelStyle}
            >
              <h2 id="guide-search-heading" className="text-xl font-bold">
                {results.length
                  ? `${results.length} ${results.length === 1 ? "guide" : "guides"} found`
                  : "No guides found"}
              </h2>
              <p
                role="status"
                className="mt-2 text-sm text-gray-500 dark:text-gray-400"
              >
                {results.length
                  ? `Results for “${query.trim()}”. Choose a guide to see the full steps.`
                  : `No matches for “${query.trim()}”. Try “narration”, “keys”, or “export”.`}
              </p>
              <ul className="mt-5 space-y-3">
                {results.map((item) => (
                  <li key={item.id}>
                    <Link
                      to={topicLink(item.id)}
                      onClick={() => setQuery("")}
                      className="block rounded-xl border border-gray-200 p-4 hover:border-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-700"
                    >
                      <span className="text-xs font-medium text-blue-600 dark:text-blue-300">
                        {item.group}
                      </span>
                      <h3 className="mt-1 font-semibold">{item.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-gray-500 dark:text-gray-400">
                        {item.description}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                onClick={() => setQuery("")}
                className={`mt-5 text-sm ${linkStyle}`}
              >
                Clear search
              </button>
            </section>
          ) : (
            <article
              id={topic.id}
              aria-labelledby="guide-topic-heading"
              className={`scroll-mt-6 ${panelStyle}`}
            >
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3 text-xs font-medium text-gray-500 dark:text-gray-400">
                <span className="flex items-center gap-2">
                  <HiOutlineBookOpen aria-hidden="true" className="h-4 w-4" />
                  {topic.group}
                </span>
                <span>{topic.steps.length} steps</span>
              </div>
              <h2
                ref={heading}
                id="guide-topic-heading"
                tabIndex={-1}
                className="scroll-mt-6 rounded text-2xl font-bold tracking-tight focus:outline-none sm:text-3xl"
              >
                {topic.title}
              </h2>
              <p className="mt-3 text-sm leading-7 text-gray-500 dark:text-gray-400">
                {topic.description}
              </p>
              <dl className="my-6 grid gap-4 rounded-2xl bg-gray-50 p-4 sm:grid-cols-2 sm:p-5 dark:bg-gray-900/50">
                <div>
                  <dt className="text-xs font-bold">Before you start</dt>
                  <dd className="mt-2 text-xs leading-6 text-gray-600 dark:text-gray-400">
                    {topic.needs}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-bold">You’ll finish with</dt>
                  <dd className="mt-2 text-xs leading-6 text-gray-600 dark:text-gray-400">
                    {topic.result}
                  </dd>
                </div>
              </dl>
              {topic.id === "edit" && (
                <div className="mb-6">
                  <EditorMap />
                </div>
              )}
              <ol className="space-y-7">
                {topic.steps.map(([title, body], index) => (
                  <li key={title} className="flex gap-3 sm:gap-4">
                    <span
                      aria-hidden="true"
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-bold text-blue-700 dark:bg-blue-500/10 dark:text-blue-300"
                    >
                      {index + 1}
                    </span>
                    <div className="min-w-0 pt-1">
                      <h3 className="text-sm font-bold">{title}</h3>
                      <p className="mt-2 text-sm leading-7 text-gray-600 dark:text-gray-300">
                        {body}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
              <p className="my-6 rounded-xl border-l-4 border-blue-400 bg-blue-50/60 p-4 text-xs leading-6 text-blue-900 dark:bg-blue-500/10 dark:text-blue-200">
                {topic.tip}
              </p>
              {topic.id === "troubleshooting" && (
                <section
                  aria-label="Common problems"
                  className="mb-6 space-y-3"
                >
                  {guideProblems.map(([title, body]) => (
                    <details
                      key={title}
                      className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"
                    >
                      <summary className="cursor-pointer text-sm font-semibold">
                        {title}
                      </summary>
                      <p className="mt-3 text-sm leading-7 text-gray-600 dark:text-gray-300">
                        {body}
                      </p>
                    </details>
                  ))}
                </section>
              )}
              <Link
                to={topic.action[0]}
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
              >
                {topic.action[1]}
                <HiOutlineArrowRight
                  aria-hidden="true"
                  className="h-4 w-4 shrink-0"
                />
              </Link>
              <nav
                aria-label="Related guides"
                className="mt-7 border-t border-gray-200 pt-5 dark:border-gray-700"
              >
                <p className="mb-3 text-xs font-semibold text-gray-500 dark:text-gray-400">
                  Keep going
                </p>
                <ul className="flex flex-wrap gap-x-5 gap-y-3">
                  {topic.related.map((id) => (
                    <li key={id}>
                      <Link
                        to={topicLink(id)}
                        className={`text-xs ${linkStyle}`}
                      >
                        {guideTopics.find((item) => item.id === id).title}
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
            </article>
          )}
        </div>
      </div>
    </HelpLayout>
  );
}
