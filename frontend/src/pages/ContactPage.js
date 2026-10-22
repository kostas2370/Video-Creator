import React, { useState } from "react";
import { Link } from "react-router-dom";
import { axiosInstance } from "../api/axiosPrivate";
import { request } from "../api/request";
import { legalContact } from "../content/legal";

const inputClass = "mt-2 w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60 dark:border-gray-600 dark:bg-gray-900 dark:text-white";

export default function ContactPage() {
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    const data = Object.fromEntries(new FormData(event.currentTarget));
    setBusy(true);
    setError("");
    const result = await request({ method: "post", url: "contact/", data, client: axiosInstance, notifyError: false });
    setBusy(false);
    if (result.ok) setSent(true);
    else setError(result.status === 429 ? "You've sent several messages. Please try again in an hour or email us directly." : result.message);
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6 sm:py-16">
      <Link to="/" className="text-sm font-semibold text-blue-600 underline underline-offset-4 dark:text-blue-400">Viddie home</Link>
      <section className="mt-8 rounded-2xl border border-gray-200 bg-white p-6 sm:p-10 dark:border-gray-700 dark:bg-gray-800">
        <h1 className="text-3xl font-bold tracking-tight">Contact us</h1>
        <p className="mt-3 text-gray-600 dark:text-gray-300">Have a question, feedback, or need help with a video? Send us a message.</p>
        {sent ? (
          <div role="status" className="mt-8 rounded-xl bg-green-50 p-5 text-green-800 dark:bg-green-950 dark:text-green-200">
            <h2 className="font-semibold">Thanks for reaching out!</h2>
            <p className="mt-2">Your message has been sent. We'll reply to the email address you provided.</p>
            <button type="button" onClick={() => setSent(false)} className="mt-4 underline underline-offset-4">Send another message</button>
          </div>
        ) : (
          <form onSubmit={submit} className="mt-8 space-y-5" aria-busy={busy}>
            <div><label htmlFor="contact-name" className="text-sm font-medium">Name</label><input id="contact-name" name="name" autoComplete="name" required maxLength={100} disabled={busy} className={inputClass} /></div>
            <div><label htmlFor="contact-email" className="text-sm font-medium">Email</label><input id="contact-email" name="email" type="email" autoComplete="email" required maxLength={254} disabled={busy} className={inputClass} /></div>
            <div><label htmlFor="contact-message" className="text-sm font-medium">Message</label><textarea id="contact-message" name="message" required minLength={10} maxLength={5000} rows={6} disabled={busy} className={inputClass} /><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">10–5,000 characters. Please don't include passwords or API keys.</p></div>
            <div className="hidden" aria-hidden="true"><label htmlFor="contact-website">Website</label><input id="contact-website" name="website" tabIndex={-1} autoComplete="off" maxLength={200} /></div>
            <p className="text-sm text-gray-500 dark:text-gray-400">We'll use your details to respond to your message. Read our <Link to="/privacy/" className="underline underline-offset-4">Privacy Policy</Link>.</p>
            {error && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <button type="submit" disabled={busy} className="w-full rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-60">{busy ? "Sending…" : "Send message"}</button>
          </form>
        )}
        <p className="mt-6 text-sm text-gray-500 dark:text-gray-400">Prefer email? <a href={`mailto:${legalContact.email}`} className="break-all text-blue-600 underline underline-offset-4 dark:text-blue-400">{legalContact.email}</a></p>
      </section>
    </main>
  );
}
