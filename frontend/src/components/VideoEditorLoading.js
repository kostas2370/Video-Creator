import React, { useLayoutEffect } from "react";
import { useLocation } from "react-router-dom";

import { isVideoEditorPath } from "../utils/pageLayout";

// Runs outside Suspense so a library's scroll position never reaches the editor,
// even while its route bundle is still loading. The library restores its own scroll.
export function VideoEditorEntry() {
  const { pathname } = useLocation();
  useLayoutEffect(() => {
    if (isVideoEditorPath(pathname)) window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [pathname]);
  return null;
}

export function VideoEditorLoading() {
  return (
    <main aria-label="Loading video editor" aria-busy="true" className="editor-workspace mx-auto min-h-[calc(100svh-64px)] max-w-[1600px] px-4 py-5 sm:px-6">
      <p role="status" className="sr-only">Loading video editor…</p>
      <div aria-hidden="true" className="motion-safe:animate-pulse">
        <div className="h-5 w-24 rounded bg-gray-200 dark:bg-gray-700" />
        <div className="mb-5 mt-3 space-y-3"><div className="h-3 w-24 rounded bg-gray-200 dark:bg-gray-700" /><div className="h-7 w-64 max-w-full rounded bg-gray-200 dark:bg-gray-700" /></div>
        <div className="mb-5 h-28 rounded-2xl border border-blue-200 bg-blue-50/70 dark:border-blue-500/25 dark:bg-blue-500/10" />
        <div className="mb-5 h-28 rounded-2xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" />
        <div className="mb-3 h-9 w-40 rounded bg-gray-200 dark:bg-gray-700" />
        <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
          <div className="h-16 border-b border-gray-200 dark:border-gray-700" />
          <div className="studio-layout">
            <div className="studio-stage"><div className="mb-5 h-9 w-48 max-w-full rounded-xl bg-gray-200 dark:bg-gray-700" /><div className="mx-auto aspect-video w-full max-w-2xl rounded-xl bg-gray-200 dark:bg-gray-900" /><div className="mt-4 h-10 rounded-xl bg-gray-200 dark:bg-gray-700" /></div>
            <div className="studio-inspector p-5"><div className="mb-6 h-10 rounded-lg bg-gray-100 dark:bg-gray-700" /><div className="h-48 rounded-xl bg-gray-100 dark:bg-gray-900" /></div>
          </div>
        </div>
      </div>
    </main>
  );
}
