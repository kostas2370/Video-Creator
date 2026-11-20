import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { HiArrowUpRight, HiMoon, HiSun } from "react-icons/hi2";
import { getSharedVideo } from "../api/apiService";
import "./SharedVideoPage.css";

export default function SharedVideoPage({ theme, toggleTheme }) {
  const { token } = useParams();
  const [result, setResult] = useState(null);
  const [playbackError, setPlaybackError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setResult(null);
    setPlaybackError(false);
    getSharedVideo(token, controller.signal).then(response => {
      if (!controller.signal.aborted) setResult(response);
    });
    return () => controller.abort();
  }, [token]);
  useEffect(() => {
    const previousTitle = document.title;
    document.title = result?.ok ? `${result.data.title} · Viddie` : "Shared video · Viddie";
    const metas = [ ["robots", "noindex, nofollow"], ["referrer", "no-referrer"] ].map(([name, content]) => {
      const meta = document.createElement("meta");
      meta.name = name;
      meta.content = content;
      document.head.appendChild(meta);
      return meta;
    });
    return () => { document.title = previousTitle; metas.forEach(meta => meta.remove()); };
  }, [result]);

  const video = result?.ok ? result.data : null;
  const unavailable = result && !result.ok;
  return <main className="public-page shared-page">
    <header className="shared-header">
      <Link to="/" className="shared-brand" aria-label="Viddie home"><img src="/viddie-icon.svg" alt="" />Viddie<span>A SPACE FOR STORIES</span></Link>
      <div className="shared-header-actions"><button type="button" className="shared-theme" onClick={toggleTheme} aria-label={theme === "dark" ? "Use light theme" : "Use dark theme"}>{theme === "dark" ? <HiSun /> : <HiMoon />}</button><Link to="/register/" className="shared-create">Create with Viddie <HiArrowUpRight aria-hidden="true" /></Link></div>
    </header>
    <section className="shared-content" aria-label="Shared video">
      <p className="shared-eyebrow">MADE WITH VIDDIE · SHARED WITH YOU</p>
      {!result && <div className="public-card shared-message" role="status">Loading video…</div>}
      {unavailable && <div className="public-card shared-message" role="alert"><span className="shared-message-icon" aria-hidden="true">↗</span><h1>{result.status === 404 ? "This video isn’t available" : "Unable to load this video"}</h1><p className="public-muted">{result.status === 404 ? "The link may have expired or the creator may have stopped sharing it. Ask them for a new link." : "Check your connection and try refreshing the page."}</p></div>}
      {video && <>
        <div className="shared-player"><video key={video.media_url} controls playsInline preload="metadata" aria-label={video.title} onError={() => setPlaybackError(true)} src={video.media_url} referrerPolicy="no-referrer" /></div>
        {playbackError && <p role="alert" className="shared-playback-error">The video could not be played. Refresh the page or ask the creator to check the link.</p>}
        <article className="shared-details">
          <div className="shared-title-row"><h1>{video.title}</h1><span className="shared-badge"><img src="/viddie-icon.svg" alt="" />Created with Viddie</span></div>
          {video.description && <p className="shared-description public-muted">{video.description}</p>}
          {video.tags.length > 0 && <ul className="shared-tags" aria-label="Video tags">{video.tags.map(tag => <li key={tag}>{tag.startsWith("#") ? tag : `#${tag}`}</li>)}</ul>}
        </article>
      </>}
      <aside className="shared-invite"><div><h2>Your next story starts with an idea.</h2><p className="public-muted">Bring it to life with Viddie.</p></div><Link to="/register/">Make your own video <HiArrowUpRight aria-hidden="true" /></Link></aside>
    </section>
  </main>;
}
