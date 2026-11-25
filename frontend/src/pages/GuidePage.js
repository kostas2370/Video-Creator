import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  HiCheck,
  HiOutlineLightBulb,
  HiOutlineCheckCircle,
  HiOutlineBookOpen,
  HiOutlineFilm,
  HiOutlineMagnifyingGlass,
  HiOutlineScissors,
  HiOutlineSparkles,
} from "react-icons/hi2";
import { HelpLayout } from "../components/help/HelpLayout";
import { GuideScreenshots } from "../components/help/GuideScreenshots";
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
    <figure className="guide-editor-map">
      <figcaption>Editor map · simplified layout</figcaption>
      <div className="guide-editor-map-body">
        <div className="guide-map-preview">
          <HiOutlineFilm aria-hidden="true" />
          <strong>Scene preview</strong>
          <span>Check the picture and sound</span>
        </div>
        <div className="guide-map-controls">
          <p>Scene controls</p>
          <ul>
            {["Script", "Visual", "Audio", "Captions", "Timing"].map(
              (label) => (
                <li key={label}>{label}</li>
              ),
            )}
          </ul>
          <p>Select a tab to change that part of the current scene.</p>
        </div>
        <div className="guide-map-storyboard">
          <strong>Storyboard</strong>
          <ol>
            {[1, 2, 3].map((number) => (
              <li key={number}>Scene {number}</li>
            ))}
          </ol>
          <p>Select a scene here. Reorder it to change the sequence.</p>
        </div>
      </div>
    </figure>
  );
}

export default function GuidePage({ theme, toggleTheme }) {
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
      theme={theme}
      toggleTheme={toggleTheme}
      title="Your next video, step by step"
      headline={
        <>
          Your next video,
          <br />
          <span>step by step</span>
        </>
      }
      description="Pick what you want to make. Get the setup, the exact steps, and a clear next move."
      eyebrow="The Viddie guide"
    >
      <section aria-labelledby="guide-start-heading" className="guide-start">
        <div className="guide-start-heading">
          <div>
            <p className="help-eyebrow">Find your starting point</p>
            <h2 id="guide-start-heading">
              New here? Start with what you have.
            </h2>
          </div>
          <span>Three ways to make a first project</span>
        </div>
        <div className="guide-start-grid">
          {startingPoints.map(({ id, label, detail, icon: Icon }) => (
            <Link
              key={id}
              to={topicLink(id)}
              onClick={() => setQuery("")}
              className="guide-start-card"
            >
              <span className="guide-start-icon">
                <Icon aria-hidden="true" />
              </span>
              <strong>{label}</strong>
              <span>{detail}</span>
              <span className="guide-start-link">Explore this guide</span>
            </Link>
          ))}
        </div>
      </section>
      <div className="guide-workspace">
        <aside className="guide-sidebar">
          <label htmlFor="guide-topic" className="guide-mobile-label">
            Choose a guide
          </label>
          <select
            id="guide-topic"
            value={topic.id}
            onChange={(event) => {
              setQuery("");
              navigate(topicLink(event.target.value));
            }}
            className="guide-topic-select"
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
          <nav aria-label="Guide contents" className="guide-contents">
            {groups.map((group) => (
              <div key={group}>
                <h2>{group}</h2>
                <ul>
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
                        >
                          {item.title}
                        </Link>
                      </li>
                    ))}
                </ul>
              </div>
            ))}
          </nav>
          <div className="guide-sidebar-support">
            <HiOutlineBookOpen aria-hidden="true" />
            <strong>A little extra help?</strong>
            <p>Tell us where you got stuck. We’re listening.</p>
            <Link to="/contact/">Get in touch</Link>
          </div>
        </aside>
        <div className="guide-reader">
          <div className="guide-search">
            <label htmlFor="guide-search">Search the guide</label>
            <div className="guide-search-field">
              <HiOutlineMagnifyingGlass aria-hidden="true" />
              <input
                id="guide-search"
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Escape") setQuery("");
                }}
                placeholder="Try missing audio, export, or API keys"
              />
            </div>
          </div>
          {words.length > 0 ? (
            <section
              aria-labelledby="guide-search-heading"
              className="guide-article guide-search-results"
            >
              <p className="help-eyebrow">A little clarity, right here</p>
              <h2 id="guide-search-heading">
                {results.length
                  ? `${results.length} ${results.length === 1 ? "guide" : "guides"} found`
                  : "No guides found"}
              </h2>
              <p role="status" className="guide-description">
                {results.length
                  ? `Results for “${query.trim()}”. Choose a guide to see the full steps.`
                  : `No matches for “${query.trim()}”. Try “narration”, “keys”, or “export”.`}
              </p>
              <ul>
                {results.map((item) => (
                  <li key={item.id}>
                    <Link to={topicLink(item.id)} onClick={() => setQuery("")}>
                      <span>{item.group}</span>
                      <h3>{item.title}</h3>
                      <p>{item.description}</p>
                    </Link>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                onClick={() => setQuery("")}
                className="help-link"
              >
                Clear search
              </button>
            </section>
          ) : (
            <article
              id={topic.id}
              aria-labelledby="guide-topic-heading"
              className="guide-article"
            >
              <div className="guide-article-meta">
                <span>
                  <HiOutlineBookOpen aria-hidden="true" />
                  {topic.group}
                </span>
                <span>{topic.steps.length} steps</span>
              </div>
              <h2 ref={heading} id="guide-topic-heading" tabIndex={-1}>
                {topic.title}
              </h2>
              <p className="guide-description">{topic.description}</p>
              <dl className="guide-essentials">
                <div>
                  <dt>
                    <HiOutlineLightBulb aria-hidden="true" />
                    Before you start
                  </dt>
                  <dd>{topic.needs}</dd>
                </div>
                <div>
                  <dt>
                    <HiOutlineCheckCircle aria-hidden="true" />
                    You’ll finish with
                  </dt>
                  <dd>{topic.result}</dd>
                </div>
              </dl>
              <GuideScreenshots
                key={topic.id}
                topicId={topic.id}
                title={topic.title}
              />
              {topic.id === "edit" && <EditorMap />}
              <ol className="guide-steps">
                {topic.steps.map(([title, body], index) => (
                  <li key={title}>
                    <span className="guide-step-number" aria-hidden="true">
                      {index + 1}
                    </span>
                    <div>
                      <h3>{title}</h3>
                      <p>{body}</p>
                    </div>
                  </li>
                ))}
              </ol>
              <div className="guide-tip">
                <HiOutlineLightBulb aria-hidden="true" />
                <div>
                  <strong>A little tip</strong>
                  <p>{topic.tip}</p>
                </div>
              </div>
              {topic.id === "troubleshooting" && (
                <section
                  aria-label="Common problems"
                  className="guide-problems"
                >
                  {guideProblems.map(([title, body]) => (
                    <details key={title}>
                      <summary>{title}</summary>
                      <p>{body}</p>
                    </details>
                  ))}
                </section>
              )}
              <Link to={topic.action[0]} className="help-primary-button">
                {topic.action[1]}
                <HiCheck aria-hidden="true" />
              </Link>
              <nav aria-label="Related guides" className="guide-related">
                <p>Keep going</p>
                <ul>
                  {topic.related.map((id) => (
                    <li key={id}>
                      <Link to={topicLink(id)}>
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
