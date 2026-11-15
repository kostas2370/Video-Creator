import React from "react";
import { Link } from "react-router-dom";
import { HiArrowRight, HiCheck, HiPlay } from "react-icons/hi2";
import { LegalFooter } from "./LegalFooter";
import "./AuthLayout.css";

function CreativePanel() {
  return (
    <aside className="auth-story" aria-label="Create with Viddie">
      <Link to="/" className="auth-brand" aria-label="Viddie home">
        <img src="/viddie-icon.svg" alt="" />
        Viddie
        <span>YOUR CREATIVE SPACE</span>
      </Link>
      <div className="auth-story-content">
        <p className="auth-eyebrow">A LITTLE IDEA. A BIGGER STORY.</p>
        <h2>Your next great<br />video starts here<span>.</span></h2>
        <p>Bring your ideas to life with stories, captions, and a little creative freedom.</p>
        <div className="auth-art" aria-hidden="true">
          <div className="auth-orbit" />
          <div className="auth-film auth-film-back"><span>THE WORLD IS YOUR CANVAS</span></div>
          <div className="auth-film auth-film-front">
            <div className="auth-film-top"><span>STORY / 01</span><span>00:12</span></div>
            <div className="auth-landscape" />
            <div className="auth-film-title">Make something<br /><em>worth watching.</em></div>
            <div className="auth-film-bottom"><HiPlay /><span>YOUR VISION, IN MOTION</span></div>
          </div>
          <div className="auth-art-badge"><HiCheck /> From idea to video</div>
          <div className="auth-timeline"><span /><span /><span /><span /><i /></div>
        </div>
      </div>
      <p className="auth-story-footer">A space for your ideas to become something more.</p>
    </aside>
  );
}

export function AuthLayout({ children, register = false }) {
  return (
    <main className="auth-page">
      <CreativePanel />
      <section className="auth-form-panel" aria-labelledby="auth-title">
        <div className="auth-topbar">
          <Link to="/" className="auth-mobile-brand">
            <img src="/viddie-icon.svg" alt="" />Viddie
          </Link>
          <span>
            {register ? "Already a creator?" : "New to Viddie?"}{" "}
            <Link to={register ? "/login/" : "/register/"}>
              {register ? "Sign in" : "Create an account"} <HiArrowRight />
            </Link>
          </span>
        </div>
        <div className="auth-form-content">{children}</div>
        <LegalFooter compact />
      </section>
    </main>
  );
}
