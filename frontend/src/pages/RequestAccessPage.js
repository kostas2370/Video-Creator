import { useRef, useState } from "react";
import { HiCheck, HiOutlineEnvelope, HiOutlineSparkles } from "react-icons/hi2";
import { PublicHeader } from "../components/PublicHeader";
import "./LandingPage.css";
import { Link } from "react-router-dom";
import { requestAccess } from "../api/apiService";
import { useDeployment } from "../store/DeploymentContext";

const inputClass = "access-input";

export default function RequestAccessPage({ theme, toggleTheme }) {
  const { invite_only: inviteOnly } = useDeployment();
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const submitting = useRef(false);

  async function submit(event) {
    event.preventDefault();
    if (submitting.current) return;
    const data = Object.fromEntries(new FormData(event.currentTarget));
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await requestAccess(data);
      if (result.ok) setSent(true);
      else
        setError(
          result.status === 429
            ? "Too many requests. Please try again in an hour."
            : result.message ||
                "We couldn’t send your request. Please try again.",
        );
    } catch {
      setError("We couldn’t send your request. Please try again.");
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return (
    <main className="access-page">
      <PublicHeader theme={theme} toggleTheme={toggleTheme} compact />
      <div className="access-layout landing-container">
        <section className="access-intro" aria-labelledby="access-title">
          <p className="landing-pill">
            <HiOutlineSparkles aria-hidden="true" />A small beta. Big
            possibilities.
          </p>
          <h1 id="access-title">
            You have a story.
            <br />
            <span>
              Let’s give it{" "}
              <br />a screen.
            </span>
          </h1>
          <p>
            A space for the ideas you haven’t quite made yet. Tell us what
            you’re thinking. We’d love to hear it.
          </p>
          <ul className="access-steps">
            <li>
              <HiCheck aria-hidden="true" />
              <span>Tell us what you’d like to create.</span>
            </li>
            <li>
              <HiCheck aria-hidden="true" />
              <span>We review every request personally.</span>
            </li>
            <li>
              <HiCheck aria-hidden="true" />
              <span>If approved, an invitation lands in your inbox.</span>
            </li>
          </ul>
          <div className="access-preview">
            <img
              src="/showcase/emu-war.jpg"
              alt="A scene from the featured Great Emu War video"
              width="480"
              height="360"
            />
            <div>
              <span>From a little curiosity</span>
              <strong>to something worth watching.</strong>
            </div>
          </div>
          <Link to="/" className="landing-inline-link">
            Explore Viddie
          </Link>
        </section>
        <section className="access-card" aria-labelledby="access-form-title">
          {sent ? (
            <div role="status" className="access-success">
              <span className="access-success-icon">
                <HiOutlineEnvelope aria-hidden="true" />
              </span>
              <p className="landing-eyebrow">The first step is yours</p>
              <h2 id="access-form-title">Your request is in.</h2>
              <p>
                If approved, you’ll receive an invitation by email. You don’t
                have an account yet; no password is needed until registration.
              </p>
              <Link to="/" className="landing-button landing-button-secondary">
                Back to Viddie
              </Link>
            </div>
          ) : (
            <>
              <p className="landing-eyebrow">Your next chapter</p>
              <h2 id="access-form-title">Request early access.</h2>
              <p className="access-card-description">
                A few details. A personal welcome. Your creative space awaits.
              </p>
              {!inviteOnly && (
                <p className="access-open-notice">
                  Registration is open.{" "}
                  <Link to="/register/">Create an account</Link>.
                </p>
              )}
              <form onSubmit={submit} className="access-form" aria-busy={busy}>
                <fieldset disabled={busy}>
                  <div>
                    <label htmlFor="access-name">Your name</label>
                    <input
                      id="access-name"
                      name="name"
                      required
                      maxLength={100}
                      autoComplete="name"
                      placeholder="Your name"
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label htmlFor="access-email">Email address</label>
                    <input
                      id="access-email"
                      name="email"
                      type="email"
                      required
                      maxLength={254}
                      autoComplete="email"
                      placeholder="you@example.com"
                      aria-describedby="access-email-guidance"
                      className={inputClass}
                    />
                    <p id="access-email-guidance" className="access-field-note">
                      Use this same email address when you register.
                    </p>
                  </div>
                  <div>
                    <label htmlFor="access-message">
                      What would you like to create?
                    </label>
                    <textarea
                      id="access-message"
                      name="message"
                      required
                      minLength={10}
                      maxLength={2000}
                      rows={4}
                      placeholder="An idea, a channel, a story you can’t stop thinking about…"
                      aria-describedby="access-guidance"
                      className={inputClass}
                    />
                    <p id="access-guidance" className="access-field-note">
                      10–2,000 characters. Please don’t include passwords or API
                      keys.
                    </p>
                  </div>
                  <div className="hidden" aria-hidden="true">
                    <label htmlFor="access-website">Website</label>
                    <input
                      id="access-website"
                      name="website"
                      tabIndex={-1}
                      autoComplete="off"
                      maxLength={200}
                    />
                  </div>
                  {error && (
                    <p role="alert" className="access-error">
                      {error}
                    </p>
                  )}
                  <button
                    type="submit"
                    className="landing-button landing-button-primary access-submit"
                  >
                    {busy ? "Sending request…" : "Request access"}
                    {!busy && <HiOutlineSparkles aria-hidden="true" />}
                  </button>
                  <p className="access-privacy">
                    We store your details to review your request and send your
                    invitation. AI features use your own provider keys; provider
                    charges may apply. Read our{" "}
                    <Link to="/privacy/">Privacy Policy</Link>.
                  </p>
                </fieldset>
              </form>
            </>
          )}
          <p className="access-card-footer">
            Already invited? <Link to="/register/">Register</Link>. Already a
            creator? <Link to="/login/">Sign in</Link>.
          </p>
        </section>
      </div>
    </main>
  );
}
