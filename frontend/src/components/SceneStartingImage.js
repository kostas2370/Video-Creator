import { GenerationCost } from "./GenerationCost";
import { SceneImageReview } from "./SceneImageReview";
import { PromptRewrite } from "./PromptRewrite";
import React, { useState } from "react";
import { API_HOST } from "../endpoints";
import { useObjectUrl } from "../hooks/useObjectUrl";
import { useStartingImage } from "../hooks/useStartingImage";
import { RememberedDetails } from "./ui/RememberedDetails";
import { editorInput } from "./ui/EditorDialog";

export const SceneStartingImage = ({ generationMode = "STANDARD", scene, index, disabled, onSaved }) => {
  const { description, setDescription, file, setFile, busy, error, edited, blocked, run } = useStartingImage(scene, { disabled, onSaved });
  const [changingImage, setChangingImage] = useState(false);
  const preview = useObjectUrl(file);
  const approved = scene.starting_image_status === "approved";
  const approvalLabel = busy === "approve" ? "Approving…" : "Approve starting image";
  const animationLabel = busy === "animate" ? "Animating…" : scene.starting_image_context?.animation_error ? "Retry animation" : "Animate approved image";
  const primaryAction = approved ? "animate" : "approve";
  const primaryLabel = approved ? animationLabel : approvalLabel;
  const useSuggestion = value => {
    setDescription(value);
    setChangingImage(true);
  };
  const savedError = scene.starting_image_context?.preparation_error || scene.starting_image_context?.animation_error;
  const buttonClass = "rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50";
  const startingImage = (preview || scene.starting_image) && <img src={preview || API_HOST + scene.starting_image} alt={`Scene ${index + 1} ${scene.starting_image_required ? "starting image to review" : "saved starting image"}`} className="mt-3 max-h-64 w-full rounded-xl object-contain" />;
  const failure = (error || savedError) && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-400">{error || savedError}</p>;
  if (!scene.starting_image_required) return <RememberedDetails videoId={scene.video} panel={`startingImage:${scene.id}`} defaultOpen={!scene.scene_image?.file} className="mt-4">
    <summary className="cursor-pointer text-sm font-medium text-gray-600 dark:text-gray-300">Saved starting image</summary>
    <a href={API_HOST + scene.starting_image} target="_blank" rel="noreferrer">{startingImage}</a>
    <p className="mt-2 text-xs text-gray-500">Saved in your media library.</p>
    {scene.starting_image_description && <button type="button" disabled={blocked} onClick={() => run("retry")} className={`${buttonClass} mt-3`}>{busy ? "Generating video…" : "Retry video with saved image"}</button>}
    {failure}
  </RememberedDetails>;
  return <RememberedDetails videoId={scene.video} panel={`startingImage:${scene.id}`} defaultOpen aria-label={`Scene ${index + 1} starting image review`} className="mt-4 rounded-xl border border-blue-200 p-4 dark:border-blue-900">
    <summary className="cursor-pointer text-sm font-semibold">Starting image · {approved ? "Approved" : "Needs review"}</summary>
    <p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">{approved ? "Ready to animate. Your current clip stays until the replacement is ready." : "Check the image, then approve it to animate."}</p>
    {startingImage}
    {scene.starting_image && <>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button type="button" disabled={blocked || edited || !!file} onClick={() => run(primaryAction)} className={buttonClass}>{primaryLabel}</button>
        {approved && <details className="text-xs text-gray-500 dark:text-gray-400"><summary className="cursor-pointer">Animation cost</summary><GenerationCost refresh={[scene, generationMode]} videoId={scene.video} sceneId={scene.id} operation="animation" /></details>}
      </div>
      <SceneImageReview key={scene.starting_image_review_key || scene.starting_asset} scene={scene} disabled={blocked || !!file} edited={edited} onUseDescription={useSuggestion} onSaved={onSaved} />
    </>}
    <details open={changingImage || !scene.starting_image} onToggle={event => setChangingImage(event.currentTarget.open)} className="mt-4 border-t border-gray-200 pt-3 dark:border-gray-700">
      <summary className="cursor-pointer text-sm font-medium text-gray-600 dark:text-gray-300">{scene.starting_image ? "Change image" : "Create starting image"}{edited && " · Unsaved changes"}</summary>
      <label className="mt-3 block text-sm">Shot description<textarea aria-label={`Scene ${index + 1} starting image description`} maxLength={2000} rows={3} value={description} disabled={blocked} onChange={event => setDescription(event.target.value)} className={`${editorInput} mt-1`} /></label>
      <PromptRewrite key={scene.id} kind="visual" scope={`starting:${scene.id}`} value={description} disabled={blocked} onUse={setDescription} />
      <GenerationCost refresh={[scene, generationMode]} videoId={scene.video} sceneId={scene.id} operation="visual" />
      <button type="button" disabled={blocked || !description.trim() || !!file} onClick={() => run("prepare")} className={`${buttonClass} mt-3`}>{busy === "prepare" ? "Preparing image…" : scene.starting_image ? "Regenerate starting image" : "Generate starting image"}</button>
      <details className="mt-4 text-sm"><summary className="cursor-pointer text-gray-500 dark:text-gray-400">Upload an image instead</summary>
        <label className="mt-3 block">Upload a replacement image<input aria-label={`Scene ${index + 1} replacement starting image`} type="file" accept="image/png,image/jpeg,image/webp" disabled={blocked} onChange={event => setFile(event.target.files?.[0] || null)} className="mt-1 block w-full text-xs" /></label>
        {file && <button type="button" disabled={blocked || !description.trim()} onClick={() => run("upload")} className={`${buttonClass} mt-3`}>{busy === "upload" ? "Uploading…" : "Save starting image"}</button>}
      </details>
      {edited && <p className="mt-3 text-xs text-amber-700 dark:text-amber-300">Generate or upload a new image to apply your description, then approve it.</p>}
    </details>
    {failure}
  </RememberedDetails>;
};
