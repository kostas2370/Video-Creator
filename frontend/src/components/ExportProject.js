import { useState } from "react";
import { HiOutlineArchiveBoxArrowDown, HiOutlineCheck } from "react-icons/hi2";
import { prepareProjectExport } from "../api/apiService";
import { editorButton } from "./ui/EditorDialog";

export function ExportProject({ video, disabled = false }) {
  const [includeOutput, setIncludeOutput] = useState(false);
  const [status, setStatus] = useState("idle");
  const busy = status === "checking";
  const [error, setError] = useState("");

  const download = async () => {
    setStatus("checking");
    setError("");
    // Preflight reports missing media and refreshes the session before a native download.
    const result = await prepareProjectExport(video.id, includeOutput);
    if (result.ok) {
      const link = document.createElement("a");
      link.href = result.data.download_url;
      link.download = result.data.filename;
      link.rel = "noreferrer";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setStatus("started");
    } else {
      setStatus("idle");
      setError(
        result.message || "The project could not be exported. Try again.",
      );
    }
  };

  return (
    <div className="space-y-5 text-sm">
      <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/50">
        <p className="font-semibold">{video.title}</p>
        <p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">
          Includes the script, active scenes, saved visual versions, captions,
          timing, effects, narration, music, and project settings. A versioned
          project.json describes everything inside.
        </p>
      </div>
      <label className="flex cursor-pointer items-start gap-3">
        <input
          type="checkbox"
          checked={includeOutput}
          onChange={(event) => setIncludeOutput(event.target.checked)}
          disabled={busy || !video.output}
          className="mt-0.5 h-4 w-4 accent-indigo-600"
        />
        <span>
          <span className="font-semibold">Include the finished video</span>
          <span className="mt-1 block text-xs text-gray-500 dark:text-gray-400">
            {video.output
              ? "Adds the latest saved export and increases the download size."
              : "Export a video first to include it in the ZIP."}
          </span>
        </span>
      </label>
      <p className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">
        Keep this ZIP as a portable backup. Project import will be added
        separately. API credentials and public share links are excluded.
      </p>
      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-300">
          {error}
        </p>
      )}
      {status === "started" && (
        <p
          role="status"
          className="flex items-start gap-2 text-sm text-emerald-700 dark:text-emerald-300"
        >
          <HiOutlineCheck
            aria-hidden="true"
            className="mt-0.5 h-4 w-4 shrink-0"
          />
          Download started. Follow its progress in your browser’s downloads.
        </p>
      )}
      <button
        type="button"
        disabled={busy || disabled}
        onClick={download}
        className={`${editorButton} w-full`}
      >
        <HiOutlineArchiveBoxArrowDown aria-hidden="true" className="h-4 w-4" />
        {busy ? "Checking project media…" : "Download project ZIP"}
      </button>
    </div>
  );
}
