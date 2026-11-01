import React, { useEffect, useState } from "react";
import { toast } from "react-toastify";
import { generateSceneImage, updateStartingImage } from "../api/apiService";
import { API_HOST } from "../endpoints";
import { useObjectUrl } from "../hooks/useObjectUrl";
import { RememberedDetails } from "./ui/RememberedDetails";
import { editorInput } from "./ui/EditorDialog";

export const SceneStartingImage = ({ scene, index, disabled, onSaved }) => {
  const [description, setDescription] = useState(scene.starting_image_description || scene.scene_image?.prompt || "");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const preview = useObjectUrl(file);
  useEffect(() => {
    setDescription(scene.starting_image_description || scene.scene_image?.prompt || "");
    setFile(null);
  }, [scene.id, scene.starting_asset, scene.starting_image_description, scene.scene_image?.prompt]);
  const approved = scene.starting_image_status === "approved";
  const edited = description.trim() !== (scene.starting_image_description || "").trim();
  const blocked = disabled || !!busy;
  const run = async operation => {
    if (blocked) return;
    setBusy(operation);
    setError("");
    try {
      const data = new FormData();
      let result;
      if (operation === "prepare" || operation === "retry") {
        data.append("image_description", description);
        result = await generateSceneImage(scene.id, data);
      } else {
        data.append("operation", operation);
        if (scene.starting_asset) data.append("asset_id", scene.starting_asset);
        if (operation === "upload") {
          data.append("image", file);
          data.append("image_description", description);
        }
        result = await updateStartingImage(scene.id, data);
      }
      if (!result?.ok) {
        setError(result?.message || "Could not finish this step. Your saved media is preserved.");
        return;
      }
      if (operation === "upload") setFile(null);
      toast.success({ prepare: "Starting image ready for review", retry: "Video is ready", upload: "Starting image ready for review", approve: "Starting image approved", animate: "Animation is ready" }[operation]);
    } catch {
      setError("Could not finish this step. Your saved media is preserved.");
    } finally {
      setBusy("");
      onSaved(true);
    }
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
    <p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Review the characters and composition, then approve the image before animating. Image generation and animation are separate paid requests. Your current clip stays until a new animation succeeds.</p>
    {startingImage}
    <label className="mt-3 block text-sm">Shot description<textarea aria-label={`Scene ${index + 1} starting image description`} maxLength={2000} rows={3} value={description} disabled={blocked} onChange={event => setDescription(event.target.value)} className={`${editorInput} mt-1`} /></label>
    <button type="button" disabled={blocked || !description.trim()} onClick={() => run("prepare")} className={`${buttonClass} mt-3`}>{busy === "prepare" ? "Preparing image…" : scene.starting_image ? "Regenerate starting image" : "Generate starting image"}</button>
    <label className="mt-3 block text-sm">Upload a replacement image<input aria-label={`Scene ${index + 1} replacement starting image`} type="file" accept="image/png,image/jpeg,image/webp" disabled={blocked} onChange={event => setFile(event.target.files?.[0] || null)} className="mt-1 block w-full text-xs" /></label>
    {file && <button type="button" disabled={blocked || !description.trim()} onClick={() => run("upload")} className={`${buttonClass} mt-3`}>{busy === "upload" ? "Uploading…" : "Save starting image"}</button>}
    {scene.starting_image && <div className="mt-3 flex flex-wrap gap-2">
      <button type="button" disabled={blocked || approved || edited || !!file} onClick={() => run("approve")} className={buttonClass}>{busy === "approve" ? "Approving…" : "Approve starting image"}</button>
      <button type="button" disabled={blocked || !approved || edited || !!file} onClick={() => run("animate")} className={buttonClass}>{busy === "animate" ? "Animating…" : scene.starting_image_context?.animation_error ? "Retry animation" : "Animate approved image"}</button>
    </div>}
    {edited && <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">Generate or upload an image for the changed description, then review and approve it.</p>}
    {failure}
  </RememberedDetails>;
};
