import React from "react";

export function ExportFailure({ video, disabled, onRetry }) {
  if (video?.status !== "FAILED" || !video.render_error?.message) return null;
  return <div role="alert" className="my-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200">
    <p className="font-semibold">Export failed</p>
    <p className="mt-1">{video.render_error.message}</p>
    {video.render_error.reference && <p className="mt-2 break-all text-xs">Reference: {video.render_error.reference}</p>}
    <button type="button" disabled={disabled} onClick={onRetry} className="mt-3 rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:opacity-40">Retry export</button>
  </div>;
}
