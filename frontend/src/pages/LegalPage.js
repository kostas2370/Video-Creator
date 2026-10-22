import React from "react";
import { Link } from "react-router-dom";
import { legalContact, legalDocuments } from "../content/legal";

function LegalText({ text }) {
  return text.split(/(https?:\/\/[^\s]+)/g).map((part, index) => {
    if (!part.startsWith("https://") && !part.startsWith("http://")) return part;
    const url = part.replace(/[.,)]+$/, "");
    return <React.Fragment key={index}><a className="break-words text-blue-600 underline underline-offset-4 dark:text-blue-400" href={url}>{url}</a>{part.slice(url.length)}</React.Fragment>;
  });
}

export function LegalFooter() {
  return (
    <footer className="border-t border-gray-200 px-6 py-6 text-sm text-gray-500 dark:border-gray-800 dark:text-gray-400">
      <nav aria-label="Legal" className="mx-auto flex max-w-4xl flex-wrap items-center justify-center gap-x-6 gap-y-3">
        <Link className="underline underline-offset-4" to="/terms/">Terms of Service</Link>
        <Link className="underline underline-offset-4" to="/privacy/">Privacy Policy</Link>
        <a className="underline underline-offset-4" href={`mailto:${legalContact.email}`}>Contact</a>
      </nav>
    </footer>
  );
}

export default function LegalPage({ document }) {
  const content = legalDocuments[document];
  return (
    <main className="mx-auto max-w-4xl px-6 py-12 sm:py-16">
      <Link to="/" className="text-sm font-semibold text-blue-600 underline underline-offset-4 dark:text-blue-400">Viddie home</Link>
      <article className="mt-8 rounded-2xl border border-gray-200 bg-white p-6 sm:p-10 dark:border-gray-700 dark:bg-gray-800">
        <h1 className="text-3xl font-bold tracking-tight">{content.title}</h1>
        <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">Last updated: {legalContact.updated}</p>
        <p className="mt-6 leading-7 text-gray-700 dark:text-gray-200"><LegalText text={content.introduction} /></p>
        {content.sections.map(section => (
          <section className="mt-8" key={section.title}>
            <h2 className="text-xl font-semibold">{section.title}</h2>
            {section.paragraphs.map(paragraph => <p className="mt-3 whitespace-pre-line leading-7 text-gray-700 dark:text-gray-200" key={paragraph}><LegalText text={paragraph} /></p>)}
          </section>
        ))}
      </article>
    </main>
  );
}
