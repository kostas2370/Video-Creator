import React from "react";
import { Link, useLocation } from "react-router-dom";
import { hasEmbeddedFooter } from "../utils/pageLayout";
import "./LegalFooter.css";

export function LegalFooter({ compact = false }) {
  const { pathname } = useLocation();
  // Authentication pages place this same footer inside the form panel.
  if (!compact && hasEmbeddedFooter(pathname)) return null;

  return (
    <footer className="site-footer">
      <nav aria-label="Help and legal">
        <Link to="/privacy/">Privacy</Link>
        <Link to="/terms/">Terms</Link>
        <Link to="/contact/">Contact</Link>
      </nav>
    </footer>
  );
}
