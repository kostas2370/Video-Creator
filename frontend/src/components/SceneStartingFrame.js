import { GenerationCost } from "./GenerationCost";
import { SceneFrameReview } from "./SceneFrameReview";
import { PromptRewrite } from "./PromptRewrite";
import React, { useState } from "react";
import { API_HOST } from "../endpoints";
import { useObjectUrl } from "../hooks/useObjectUrl";
import { useStartingFrame } from "../hooks/useStartingFrame";
import { RememberedDetails } from "./ui/RememberedDetails";
import { editorInput } from "./ui/EditorDialog";

export const SceneStartingFrame = ({ generationMode = "STANDARD", scene, index, disabled, onSaved }) => {
  const { description, setDescription, file, setFile, busy, error, edited, blocked, run } = useStartingFrame(scene, { disabled, onSaved });
  const [changingImage, setChangingImage] = useState(false);
  const preview = useObjectUrl(file);
  const approved = scene.starting_frame_status === "approved";
  const approvalLabel = busy === "approve" ? "Approving…" : "Approve starting frame";
  const animationLabel = busy === "animate" ? "Animating…" : scene.starting_frame_context?.animation_error ? "Retry animation" : "Animate approved frame";
  const primaryAction = approved ? "animate" : "approve";
  const primaryLabel = approved ? animationLabel : approvalLabel;
  const useSuggestion = value => {
    setDescription(value);
    setChangingImage(true);
  };
  const savedError = scene.starting_frame_context?.preparation_error || scene.starting_frame_context?.animation_error;
  const buttonClass = "rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50";
  const startingFrame = (preview || scene.starting_frame) && <img src={preview || API_HOST + scene.starting_frame} alt={`Scene ${index + 1} ${scene.starting_frame_required ? "starting frame to review" : "saved starting frame"}`} className="mt-3 max-h-64 w-full rounded-xl object-contain" />;
  const failure = (error || savedError) && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-400">{error || savedError}</p>;
  if (!scene.starting_frame_required) return <RememberedDetails videoId={scene.video} panel={`startingFrame:${scene.id}`} defaultOpen={!scene.scene_image?.file} className="mt-4">
    <summary className="cursor-pointer text-sm font-medium text-gray-600 dark:text-gray-300">Saved starting frame</summary>
    <a href={API_HOST + scene.starting_frame} target="_blank" rel="noreferrer">{startingFrame}</a>
    <p className="mt-2 text-xs text-gray-500">Saved in your media library.</p>
    {scene.starting_frame_description && <button type="button" disabled={blocked} onClick={() => run("retry")} className={`${buttonClass} mt-3`}>{busy ? "Generating video…" : "Retry video with saved frame"}</button>}
    {failure}
  </RememberedDetails>;
  return <RememberedDetails videoId={scene.video} panel={`startingFrame:${scene.id}`} defaultOpen aria-label={`Scene ${index + 1} starting frame review`} className="mt-4 rounded-xl border border-blue-200 p-4 dark:border-blue-900">
    <summary className="cursor-pointer text-sm font-semibold">Starting frame · {!scene.starting_frame ? "Not prepared" : approved ? "Approved" : "Needs review"}</summary>
    <p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">{!scene.starting_frame ? "Create a frame to review before animating. Your current clip stays until the replacement is ready." : approved ? "Ready to animate. Your current clip stays until the replacement is ready." : "Check the frame, then approve it to animate."}</p>
    {startingFrame}
    {scene.starting_frame && <>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button type="button" disabled={blocked || edited || !!file} onClick={() => run(primaryAction)} className={buttonClass}>{primaryLabel}</button>
        {approved && <details className="text-xs text-gray-500 dark:text-gray-400"><summary className="cursor-pointer">Animation cost</summary><GenerationCost refresh={[scene, generationMode]} videoId={scene.video} sceneId={scene.id} operation="animation" /></details>}
      </div>
      <SceneFrameReview key={scene.starting_frame_review_key || scene.starting_asset} scene={scene} disabled={blocked || !!file} edited={edited} onUseDescription={useSuggestion} onSaved={onSaved} />
    </>}
    <details open={changingImage || !scene.starting_frame} onToggle={event => setChangingImage(event.currentTarget.open)} className="mt-4 border-t border-gray-200 pt-3 dark:border-gray-700">
      <summary className="cursor-pointer text-sm font-medium text-gray-600 dark:text-gray-300">{scene.starting_frame ? "Change frame" : "Create starting frame"}{edited && " · Unsaved changes"}</summary>
      <label className="mt-3 block text-sm">Shot description<textarea aria-label={`Scene ${index + 1} starting frame description`} maxLength={2000} rows={3} value={description} disabled={blocked} onChange={event => setDescription(event.target.value)} className={`${editorInput} mt-1`} /></label>
      <PromptRewrite key={scene.id} kind="visual" scope={`starting:${scene.id}`} value={description} disabled={blocked} onUse={setDescription} />
      <GenerationCost refresh={[scene, generationMode]} videoId={scene.video} sceneId={scene.id} operation="visual" />
      <button type="button" disabled={blocked || !description.trim() || !!file} onClick={() => run("prepare")} className={`${buttonClass} mt-3`}>{busy === "prepare" ? "Preparing frame…" : scene.starting_frame ? "Regenerate starting frame" : "Generate starting frame"}</button>
      <details className="mt-4 text-sm"><summary className="cursor-pointer text-gray-500 dark:text-gray-400">Upload a frame instead</summary>
        <label className="mt-3 block">Upload a replacement frame<input aria-label={`Scene ${index + 1} replacement starting frame`} type="file" accept="image/png,image/jpeg,image/webp" disabled={blocked} onChange={event => setFile(event.target.files?.[0] || null)} className="mt-1 block w-full text-xs" /></label>
        {file && <button type="button" disabled={blocked || !description.trim()} onClick={() => run("upload")} className={`${buttonClass} mt-3`}>{busy === "upload" ? "Uploading…" : "Save starting frame"}</button>}
      </details>
      {edited && <p className="mt-3 text-xs text-amber-700 dark:text-amber-300">Generate or upload a new frame to apply your description, then approve it.</p>}
    </details>
    {failure}
  </RememberedDetails>;
};
