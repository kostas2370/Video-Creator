import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { HiOutlineArrowDownTray } from "react-icons/hi2";
import { importProject } from "../api/apiService";
import {
  EditorDialog,
  editorButton,
  editorSecondaryButton,
} from "./ui/EditorDialog";

export function ImportProject() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    if (!file || busy) return;
    if (file.size > 1024 * 1024 * 1024) {
      setError("Choose a project ZIP smaller than 1 GB.");
      return;
    }
    setBusy(true);
    setError("");
    const data = new FormData();
    data.append("file", file);
    const result = await importProject(data);
    setBusy(false);
    if (result.ok) {
      setOpen(false);
      navigate(`/videos/${result.data.id}/`);
    } else {
      setError(
        result.message || "The project could not be imported. Try again.",
      );
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setFile(null);
          setError("");
          setOpen(true);
        }}
        className={editorSecondaryButton}
      >
        <HiOutlineArrowDownTray aria-hidden="true" className="h-4 w-4" />
        Import project
      </button>
      <EditorDialog
        open={open}
        onClose={() => setOpen(false)}
        busy={busy}
        title="Import project"
        description="Bring a Viddie project back into your library."
        icon={HiOutlineArrowDownTray}
        maxWidth="max-w-xl"
        footer={
          <button
            type="submit"
            form="import-project"
            disabled={!file || busy}
            className={`${editorButton} w-full`}
          >
            {busy ? "Importing project…" : "Import project ZIP"}
          </button>
        }
      >
        <form
          id="import-project"
          onSubmit={submit}
          className="space-y-5 text-sm"
        >
          <div className="rounded-2xl border border-dashed border-gray-300 bg-gray-50 p-5 dark:border-gray-600 dark:bg-gray-900/50">
            <label htmlFor="project-zip" className="block font-semibold">
              Project ZIP
            </label>
            <p
              id="project-zip-help"
              className="my-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400"
            >
              Choose a ZIP created with Viddie’s Project ZIP export. Maximum 1
              GB, including unpacked media.
            </p>
            <input
              id="project-zip"
              type="file"
              accept=".zip,application/zip"
              disabled={busy}
              aria-describedby="project-zip-help"
              onChange={(event) => {
                setFile(event.target.files?.[0] || null);
                setError("");
              }}
              className="block w-full text-xs file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:font-semibold file:text-blue-700 dark:file:bg-blue-500/10 dark:file:text-blue-300"
            />
          </div>
          <p className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">
            Creates a new private project with its packaged scenes, media, and
            settings. Your existing projects stay untouched. Select an available
            voice in Settings before regenerating narration; credentials and
            cloned-voice access are not transferred.
          </p>
          {busy && (
            <p
              role="status"
              className="text-sm text-blue-600 dark:text-blue-300"
            >
              Uploading and verifying your project. Large projects can take a
              few minutes. Keep this window open.
            </p>
          )}
          {error && (
            <p role="alert" className="text-sm text-red-600 dark:text-red-300">
              {error}
            </p>
          )}
        </form>
      </EditorDialog>
    </>
  );
}
