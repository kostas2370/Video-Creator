import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { requestAccess } from "../api/apiService";
import { useDeployment } from "../store/DeploymentContext";

const inputClass = "public-input mt-2 w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60 dark:border-gray-600 dark:bg-gray-900 dark:text-white";

export default function RequestAccessPage() {
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
      else setError(result.status === 429 ? "Too many requests. Please try again in an hour." : result.message || "We couldn’t send your request. Please try again.");
    } catch {
      setError("We couldn’t send your request. Please try again.");
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return (
    <main className="public-page mx-auto max-w-2xl px-4 py-8 sm:px-6 sm:py-16">
      <Link to="/" className="text-sm font-semibold text-blue-600 underline underline-offset-4 dark:text-blue-400">Viddie home</Link>
      <section className="public-card mt-8 rounded-3xl border border-gray-200 bg-white p-6 sm:p-10 dark:border-gray-700 dark:bg-gray-800">
        <p className="text-sm font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-300">Your next story starts here</p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight">Request early access.</h1>
        <p className="mt-4 public-muted">Tell us a little about what you want to create. We review requests personally and email approved creators an invitation to register.</p>
        {!inviteOnly && <p className="mt-4">Registration is open. <Link to="/register/" className="font-semibold text-blue-600 underline dark:text-blue-300">Create an account</Link>.</p>}
        {sent ? <div role="status" className="mt-8 rounded-xl bg-green-50 p-5 text-green-900 dark:bg-green-950 dark:text-green-200"><h2 className="text-lg font-semibold">Your request is in.</h2><p className="mt-2">If approved, you’ll receive an invitation by email. You don’t have an account yet; no password is needed until registration.</p></div> : (
          <form onSubmit={submit} className="mt-8 space-y-5" aria-busy={busy}>
            <fieldset disabled={busy} className="space-y-5">
              <div><label htmlFor="access-name">Your name</label><input id="access-name" name="name" required maxLength={100} autoComplete="name" className={inputClass} /></div>
              <div><label htmlFor="access-email">Email address</label><input id="access-email" name="email" type="email" required maxLength={254} autoComplete="email" className={inputClass} /><p className="mt-2 text-sm public-muted">Use this same email address when you register.</p></div>
              <div><label htmlFor="access-message">What would you like to create?</label><textarea id="access-message" name="message" required minLength={10} maxLength={2000} rows={4} aria-describedby="access-guidance" className={inputClass} /><p id="access-guidance" className="mt-2 text-sm public-muted">10–2,000 characters. Please don’t include passwords or API keys.</p></div>
              <div className="hidden" aria-hidden="true"><label htmlFor="access-website">Website</label><input id="access-website" name="website" tabIndex={-1} autoComplete="off" maxLength={200} /></div>
              <p className="text-sm public-muted">We store your details to review your request and send your invitation. AI features use your own provider keys; provider charges may apply. Read our <Link to="/privacy/" className="underline">Privacy Policy</Link>.</p>
              {error && <p role="alert" className="text-red-600 dark:text-red-400">{error}</p>}
              <button type="submit" className="public-button w-full rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-60">{busy ? "Sending request…" : "Request access"}</button>
            </fieldset>
          </form>
        )}
        <p className="mt-6 text-sm public-muted">Already invited? <Link to="/register/" className="font-semibold underline">Register</Link>. Already a creator? <Link to="/login/" className="font-semibold underline">Sign in</Link>.</p>
      </section>
    </main>
  );
}
