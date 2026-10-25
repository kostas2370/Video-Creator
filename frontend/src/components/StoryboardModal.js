import { API_HOST } from "../endpoints";
import { VisualContinuity } from "./VisualContinuity";
import React, { useEffect, useRef, useState } from "react";
import { EditorDialog } from "./ui/EditorDialog";
import { useNavigate } from "react-router-dom";
import { approveScript } from "../api/apiService";

const inputClass = "mt-2 w-full rounded-xl border border-gray-300 bg-white p-3 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white";

export function StoryboardModal({ open, video, onClose, onApproved }) {
  const navigate = useNavigate();
  const [script, setScript] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const initializedVideo = useRef(null);
  useEffect(() => {
    if (!video?.gpt_answer || initializedVideo.current === video.id) return;
    initializedVideo.current = video.id;
    const draft = JSON.parse(JSON.stringify(video.gpt_answer));
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
    <EditorDialog open={open} onClose={onClose} busy={busy} title="Review your storyboard" description="Review and edit the generated prompts below. Visuals and narration will be created after you press Proceed." maxWidth="max-w-5xl" footer={<div className="flex justify-end gap-3">
      <button type="button" disabled={busy} onClick={onClose} className="rounded-xl px-4 py-3 text-sm font-semibold text-gray-700 disabled:opacity-50 dark:text-gray-200">Close</button>
      <button type="submit" form="storyboard-review" disabled={busy} className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{busy ? "Starting generation…" : "Proceed"}</button>
    </div>}>
      <form id="storyboard-review" onSubmit={proceed} className="text-gray-700 dark:text-gray-200">
          <label className="block text-sm font-semibold">Video title
            <input autoFocus required maxLength={50} value={script.title} disabled={busy} onChange={event => setScript({ ...script, title: event.target.value })} className={inputClass} />
          </label>
          {video?.reference_image && <figure className="mt-5 flex items-center gap-4 rounded-xl bg-gray-50 p-3 dark:bg-gray-900"><img src={video.reference_image.startsWith("/") ? API_HOST + video.reference_image : video.reference_image} alt="Reference used to draft this storyboard" className="h-28 w-28 rounded-lg object-contain" /><figcaption className="text-sm"><span className="font-semibold">{({ character: "Character reference", style: "Style reference", both: "Character and style reference" })[video.settings?.reference_role || "both"]}</span><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Compare the visible details with the shared description below. Your written instructions take priority.</p></figcaption></figure>}
          {video?.mode === "AI" && <div className="mt-5"><VisualContinuity value={script.visual_continuity || ""} disabled={busy} description="Review the shared character and setting details drafted for your story. Edit or clear them before creating the visuals." onChange={value => setScript(current => ({ ...current, visual_continuity: value }))} /></div>}
          {script.scenes.map((scene, sceneIndex) => (
            <section key={sceneIndex} className="mt-5 rounded-2xl border border-gray-200 p-4 dark:border-gray-600">
              <h3 className="font-semibold">Scene {sceneIndex + 1}: {scene.scene}</h3>
              {scene.sentences.map((shot, shotIndex) => (
                <div key={shotIndex} className="mt-4 space-y-3">
                  {scene.sentences.length > 1 && <p className="text-xs font-semibold">Shot {shotIndex + 1}</p>}
                  {narration && <label className="block text-sm font-medium">Narration
                    <textarea required maxLength={2000} rows={2} disabled={busy} value={shot.sentence || ""} onChange={event => changeShot(sceneIndex, shotIndex, "sentence", event.target.value)} className={inputClass} />
                  </label>}
                  <label className="block text-sm font-medium">Visual prompt
                    <textarea required maxLength={2000} rows={3} disabled={busy} value={shot.image_description || ""} onChange={event => changeShot(sceneIndex, shotIndex, "image_description", event.target.value)} className={inputClass} />
                  </label>
                  {video?.settings?.ai_scene_editing && shot.editing && <p className="text-xs text-gray-500 dark:text-gray-400">
                    AI editing: {shot.editing.motion_style.toLowerCase().replaceAll("_", " ")} · {shot.editing.transition_after.toLowerCase()} · {shot.editing.pause_after}s pause. You can adjust these in the scene editor.
                  </p>}
                </div>
              ))}
            </section>
          ))}
          {error && <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-300">{error}</p>}
      </form>
    </EditorDialog>
  );
}
