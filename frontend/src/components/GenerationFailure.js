import React from "react";
import { Link } from "react-router-dom";

export function GenerationFailure({ video }) {
  const failure = video?.generation_error;
  if (video?.status !== "FAILED" || !failure?.message) return null;
  return <div role="alert" className="my-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200">
    <p className="font-semibold">Generation failed{failure.provider ? ` · ${failure.provider}` : ""}</p>
    <p className="mt-1">{failure.message}</p>
    {failure.provider && <Link to="/api-keys/" className="mt-3 inline-block font-semibold underline">Open API key settings</Link>}
  </div>;
}
