import { editableStoryboard } from "../utils/storyboard";
import { API_HOST } from "../endpoints";
import { VisualContinuity } from "./VisualContinuity";
import { ShotPlanFields } from "./ShotPlanFields";
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
    const draft = editableStoryboard(video.gpt_answer);
    if (video.mode === "AI") draft.visual_continuity = video.settings?.visual_continuity ?? draft.visual_continuity ?? "";
    setScript(draft);
    setError("");
  }, [video?.id, video?.gpt_answer]);

  const changeScene = (sceneIndex, field, value) => {
    setScript(current => ({ ...current, scenes: current.scenes.map((scene, index) => index === sceneIndex ? { ...scene, [field]: value } : scene) }));
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
              <div className="mt-4 space-y-3">
                {narration && <label className="block text-sm font-medium">Scene narration
                  <textarea required maxLength={2000} rows={4} disabled={busy} value={scene.narration || ""} onChange={event => changeScene(sceneIndex, "narration", event.target.value)} className={inputClass} />
                  <span className="mt-1 block text-xs font-normal text-gray-500">Keep the full story beat together. A scene can contain several sentences.</span>
                </label>}
                <label className="block text-sm font-medium">{scene.additional_image_descriptions?.length ? "Shot 1 visual prompt" : "Visual prompt"}
                  <textarea required maxLength={2000} rows={3} disabled={busy} value={scene.image_description || ""} onChange={event => changeScene(sceneIndex, "image_description", event.target.value)} className={inputClass} />
                </label>
                {video?.mode === "AI" && <details><summary className="cursor-pointer text-xs font-medium text-gray-500">Shot direction &amp; duration</summary><div className="mt-3"><ShotPlanFields plan={scene.shot_plan} disabled={busy} narration={narration} onChange={plan => changeScene(sceneIndex, "shot_plan", plan)} /></div></details>}
                {(scene.additional_image_descriptions || []).map((description, imageIndex) => <label key={imageIndex} className="block text-sm font-medium">Shot {imageIndex + 2} visual prompt
                  <textarea required maxLength={2000} rows={3} disabled={busy} value={description} onChange={event => changeScene(sceneIndex, "additional_image_descriptions", scene.additional_image_descriptions.map((prompt, index) => index === imageIndex ? event.target.value : prompt))} className={inputClass} />
                </label>)}
                {video?.settings?.ai_scene_editing && scene.editing && <p className="text-xs text-gray-500 dark:text-gray-400">
                  AI editing: {scene.shot_plan?.camera_movement ? "motion from shot plan" : scene.editing.motion_style.toLowerCase().replaceAll("_", " ")} · {scene.editing.transition_after.toLowerCase()} · {scene.editing.pause_after}s pause. You can adjust these in the scene editor.
                </p>}
              </div>
            </section>
          ))}
          {error && <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-300">{error}</p>}
      </form>
    </EditorDialog>
  );
}
