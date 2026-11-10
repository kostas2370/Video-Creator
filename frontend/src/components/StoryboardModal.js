import { GenerationModeSelect } from "./GenerationModeSelect";
import { GenerationCost } from "./GenerationCost";
import { StoryboardRevision } from "./StoryboardRevision";
import { StoryboardScene } from "./StoryboardScene";
import { DeleteDraftProject } from "./DeleteDraftProject";
import { API_HOST } from "../endpoints";
import { VisualContinuity } from "./VisualContinuity";
import React, { useEffect, useRef, useState } from "react";
import { EditorDialog } from "./ui/EditorDialog";
import { useNavigate } from "react-router-dom";
import { approveScript } from "../api/apiService";

const inputClass = "mt-2 w-full rounded-xl border border-gray-300 bg-white p-3 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white";

export function StoryboardModal({ open, video, onClose, onApproved, onDeleted }) {
  const navigate = useNavigate();
  const [script, setScript] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const initializedVideo = useRef(null);
  useEffect(() => {
    if (!video?.gpt_answer || initializedVideo.current === video.id) return;
    initializedVideo.current = video.id;
    const draft = JSON.parse(JSON.stringify(video.gpt_answer));
    draft.generation_mode = video.settings?.generation_mode || draft.generation_mode || "STANDARD";
    if (video.mode === "AI") draft.visual_continuity = video.settings?.visual_continuity ?? draft.visual_continuity ?? "";
    setScript(draft);
    setError("");
  }, [video?.id, video?.gpt_answer]);

  const changeShot = (sceneIndex, shotIndex, field, value) => {
    setScript(current => ({ ...current, scenes: current.scenes.map((scene, i) => i !== sceneIndex ? scene : {
      ...scene, sentences: scene.sentences.map((shot, j) => j !== shotIndex ? shot : { ...shot, [field]: value }),
    }) }));
  };
  const proceed = async event => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await approveScript(video.id, script);
      if (!result.ok) {
        setError(result.message || "Could not start generation. Check the prompts and try again.");
        return;
      }
      if (onApproved) onApproved(result.data.video);
      else navigate(`/videos/${video.id}`);
    } catch {
      setError("Could not start generation. Please try again.");
    } finally {
      setBusy(false);
    }
  };
  if (!open || !script) return null;
  const narration = video?.settings?.narration !== false;
  return (
    <EditorDialog
      open={open}
      onClose={onClose}
      busy={busy}
      title="Review your storyboard"
      description="Scan the story, expand a scene to edit, then create your video."
      maxWidth="max-w-4xl"
      footer={
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0 basis-full sm:flex-1 sm:basis-auto">
            <GenerationCost refresh={video.settings} videoId={video.id} storyboard={script} />
          </div>
          <div className="flex items-center gap-2">
            <button type="button" disabled={busy} onClick={onClose} className="rounded-xl px-4 py-3 text-sm font-semibold text-gray-500 disabled:opacity-50">Close</button>
            <button type="submit" form="storyboard-review" disabled={busy} className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:opacity-50">
              {busy ? "Starting generation…" : "Proceed"}
            </button>
          </div>
        </div>
      }
    >
      <form
        id="storyboard-review"
        onSubmit={proceed}
        onInvalidCapture={event => {
          let details = event.target.closest("details");
          while (details) {
            details.open = true;
            details = details.parentElement.closest("details");
          }
        }}
        className="space-y-5 text-gray-700 dark:text-gray-200"
      >
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500">Video title
            <input autoFocus required maxLength={50} value={script.title} disabled={busy} onChange={event => setScript({ ...script, title: event.target.value })} className={`${inputClass} text-base font-semibold`} />
          </label>
          <p className="mt-2 text-xs text-gray-500">{script.scenes.length} scenes · {narration ? "With narration" : "Visual story"} · Edit only what you want to change</p>
        </div>

        <details className="group rounded-2xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-4 text-sm font-semibold text-indigo-700 dark:text-indigo-100">
            <span>Revise storyboard with AI</span>
            <span aria-hidden="true" className="transition group-open:rotate-180">⌄</span>
          </summary>
          <div className="px-4 pb-1">
            <StoryboardRevision key={video.id} videoId={video.id} storyboard={script} disabled={busy} onApply={setScript} />
          </div>
        </details>

        <div className="space-y-3" aria-label="Storyboard scenes">
          {script.scenes.map((scene, sceneIndex) => (
            <StoryboardScene
              key={sceneIndex}
              scene={scene}
              index={sceneIndex}
              video={video}
              narration={narration}
              disabled={busy}
              onChange={(shotIndex, field, value) => changeShot(sceneIndex, shotIndex, field, value)}
            />
          ))}
        </div>

        <details className="border-t border-gray-100 pt-4 dark:border-gray-700">
          <summary className="cursor-pointer text-xs font-medium text-gray-500">Project settings &amp; character continuity</summary>
          <div className="mt-4 space-y-4">
            {video.mode === "AI" && <GenerationModeSelect value={script.generation_mode} onChange={value => setScript(current => ({ ...current, generation_mode: value }))} disabled={busy} />}
            {video.reference_image && <figure className="flex items-center gap-3 rounded-xl bg-gray-50 p-3 dark:bg-gray-900">
              <img src={video.reference_image.startsWith("/") ? API_HOST + video.reference_image : video.reference_image} alt="Reference used to draft this storyboard" className="h-20 w-20 rounded-lg object-contain" />
              <figcaption className="text-xs text-gray-500">Your reference for character appearance and visual style.</figcaption>
            </figure>}
            {video.mode === "AI" && <VisualContinuity value={script.visual_continuity || ""} disabled={busy} description="Shared details for the story. Edit or clear them before creating visuals." onChange={value => setScript(current => ({ ...current, visual_continuity: value }))} />}
            <DeleteDraftProject id={video.id} disabled={busy} onDeleted={onDeleted} />
          </div>
        </details>
        {error && <p role="alert" className="text-sm text-red-600 dark:text-red-300">{error}</p>}
      </form>
    </EditorDialog>
  );
}
