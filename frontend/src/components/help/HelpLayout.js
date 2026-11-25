import { useEffect, useRef } from "react";
import { Link, NavLink } from "react-router-dom";
import {
  HiOutlineBookOpen,
  HiOutlineFilm,
  HiOutlineSparkles,
} from "react-icons/hi2";
import useAuth from "../../hooks/useAuth";
import { PublicHeader } from "../PublicHeader";
import "./HelpPages.css";

export const linkStyle = "help-link";
export const panelStyle = "help-panel";

export function HelpLayout({
  title,
  headline,
  description,
  eyebrow = "Learn & explore",
  children,
  theme,
  toggleTheme,
}) {
  const { access_token } = useAuth();
  const content = useRef(null);
  useEffect(() => {
    const previousTitle = document.title;
    document.title = `${title} · Viddie`;
    if (!window.location.hash) window.scrollTo(0, 0);
    return () => {
      document.title = previousTitle;
    };
  }, [title]);

  return (
    <main className="help-page">
      <a href="#help-content" className="help-skip" onClick={event => { event.preventDefault(); content.current?.focus(); }}>
        Skip to the guide
      </a>
      {!access_token && (
        <PublicHeader theme={theme} toggleTheme={toggleTheme} />
      )}
      <div className="help-container">
        <header className="help-hero">
          <div>
            <Link to="/" className="help-breadcrumb">
              Viddie home
            </Link>
            <p className="help-eyebrow">
              <HiOutlineBookOpen aria-hidden="true" />
              {eyebrow}
            </p>
            <h1>{headline || title}</h1>
            <p className="help-hero-description">{description}</p>
            <nav aria-label="Help pages" className="help-page-tabs">
              {[
                { to: "/guide/", label: "Guide", icon: HiOutlineBookOpen },
                {
                  to: "/whats-new/",
                  label: "What’s new",
                  icon: HiOutlineSparkles,
                },
              ].map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to} end>
                  <Icon aria-hidden="true" />
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="help-hero-art" aria-hidden="true">
            <div className="help-art-back">
              <HiOutlineFilm />
              <span>Your creative space</span>
            </div>
            <div className="help-art-sheet">
              <span className="help-art-label">A LITTLE GUIDANCE</span>
              <HiOutlineBookOpen />
              <p>
                Find your flow.
                <br />
                <em>Make it yours.</em>
              </p>
              <div>
                <span>Create</span>
                <span>Edit</span>
                <span>Share</span>
              </div>
            </div>
            <span className="help-art-note">
              <HiOutlineSparkles />
              From first idea to final cut.
            </span>
          </div>
        </header>
        <div id="help-content" className="help-content" ref={content} tabIndex={-1}>
          {children}
        </div>
      </div>
    </main>
  );
}
