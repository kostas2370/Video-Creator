import { Link } from "react-router-dom";
import { LandingThemeToggle } from "./LandingThemeToggle";
import "./PublicHeader.css";

export function PublicHeader({
  theme,
  toggleTheme,
  home = false,
  compact = false,
}) {
  return (
    <nav
      className="landing-nav landing-container"
      aria-label="Viddie public navigation"
    >
      <Link to="/" className="landing-brand" aria-label="Viddie home">
        <img src="/viddie-icon.svg" alt="" width="36" height="36" />
        Viddie<span className="landing-beta">BETA</span>
      </Link>
      {!compact && (
        <div className="landing-nav-sections">
          <a href={home ? "#workflow" : "/#workflow"}>The studio</a>
          <a href={home ? "#showcase" : "/#showcase"}>Made with Viddie</a>
          <Link to="/guide/">Guide</Link>
        </div>
      )}
      <div className="landing-nav-actions">
        <LandingThemeToggle theme={theme} toggleTheme={toggleTheme} />
        <Link to="/login/" className="landing-sign-in">
          Sign in
        </Link>
      </div>
    </nav>
  );
}
