import { useState } from "react";
import { HiOutlinePlayCircle, HiPlay } from "react-icons/hi2";

export const showcaseVideos = [
  {
    id: "EeKK9NKiiNg",
    title: "World War II: Causes, Conflict, and Consequences",
    category: "The stories that shaped us",
    label: "History & education",
    poster: "/showcase/world-war-ii.jpg",
    tone: "showcase-blue",
  },
  {
    id: "mrEpfZUVlNA",
    title: "Australia’s Great Emu War",
    category: "A little history. A lot of emus.",
    label: "A curious piece of history",
    poster: "/showcase/emu-war.jpg",
    tone: "showcase-violet",
  },
];

export function VideoShowcase() {
  const [active, setActive] = useState(null);
  return (
    <section
      id="showcase"
      aria-labelledby="showcase-title"
      className="showcase-section"
    >
      <div className="showcase-heading">
        <div>
          <p className="landing-eyebrow">The proof is in the playback</p>
          <h2 id="showcase-title">
            Less imagining.
            <br />
            <span>More “I made that.”</span>
          </h2>
        </div>
        <p>
          Real stories, ready to watch. Explore two featured videos and see
          where a little curiosity can take you.
        </p>
      </div>
      <div className="showcase-grid">
        {showcaseVideos.map((video) => (
          <article key={video.id} className={`showcase-card ${video.tone}`}>
            <div className="showcase-player">
              {active === video.id ? (
                <iframe
                  src={`https://www.youtube-nocookie.com/embed/${video.id}?autoplay=1&rel=0`}
                  title={video.title}
                  allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
                  allowFullScreen
                  referrerPolicy="strict-origin-when-cross-origin"
                />
              ) : (
                <button
                  type="button"
                  onClick={() => setActive(video.id)}
                  aria-label={`Play ${video.title}`}
                  className="showcase-play"
                >
                  <img
                    src={video.poster}
                    alt=""
                    loading="lazy"
                    width="480"
                    height="360"
                    className="showcase-poster"
                  />
                  <span className="showcase-shade" aria-hidden="true" />
                  <span className="showcase-category">{video.label}</span>
                  <span className="showcase-play-icon">
                    <HiPlay aria-hidden="true" />
                  </span>
                  <span className="showcase-cover-title">{video.category}</span>
                  <span className="showcase-cover-label">Play the film</span>
                </button>
              )}
            </div>
            <div className="showcase-caption">
              <h3>{video.title}</h3>
              <a
                href={`https://www.youtube.com/watch?v=${video.id}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <HiOutlinePlayCircle aria-hidden="true" />
                Watch on YouTube
                <span className="sr-only"> (opens in a new tab)</span>
              </a>
            </div>
          </article>
        ))}
      </div>
      <div className="showcase-footer">
        <p>Players connect to YouTube only when you press play.</p>
        <a
          href="https://www.tiktok.com/@viddieeducation"
          target="_blank"
          rel="noopener noreferrer"
        >
          More on TikTok · @viddieeducation
          <span className="sr-only"> (opens in a new tab)</span>
        </a>
      </div>
    </section>
  );
}
