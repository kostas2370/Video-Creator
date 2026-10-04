import React, { useEffect, useState } from "react";
import { updateSceneImage, generateSceneImage } from "../api/apiService";
import { toast } from "react-toastify";
import { EditorDialog, editorInput, editorButton } from "./ui/EditorDialog";

export const EditSceneImageModal = ({ showModal, setShowModal, scene_info, setUpdate }) => {
  const [file, setFile] = useState(null);
  const [withAudio, setWithAudio] = useState(false);
  const [busy, setBusy] = useState("");
  const [description, setDescription] = useState("");
  const [mode, setMode] = useState("upload");
  const [preview, setPreview] = useState("");
  useEffect(() => {
    if (showModal) { setFile(null); setWithAudio(!!scene_info.with_audio); setDescription(scene_info.prompt || ""); setMode("upload"); }
  }, [showModal, scene_info.scene_id, scene_info.with_audio, scene_info.prompt]);
  useEffect(() => {
    if (!file) { setPreview(""); return; }
    const url = URL.createObjectURL(file); setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const run = async () => {
    setBusy(mode);
    try {
      const data = new FormData();
      let response;
      if (mode === "upload") {
        if (file) data.append("image", file);
        data.append("with_audio", withAudio ? 1 : 0);
        ({ data: response } = await updateSceneImage(scene_info.scene_id, scene_info.scene_image_id, data));
      } else {
        data.append("image_description", description);
        ({ data: response } = await generateSceneImage(scene_info.scene_id, data));
      }
      if (response) { toast.success("Scene visual updated successfully"); setUpdate(true); setShowModal(false); }
    } catch { toast.error("Could not update the visual. Please try again."); }
    finally { setBusy(""); }
  };
  const media = preview || (scene_info.scene_image_id ? scene_info.image : "");
  const isVideo = file ? file.type.startsWith("video/") : media?.includes("mp4");
  const previewAspectRatio = { LANDSCAPE: "16 / 9", PORTRAIT: "9 / 16", SQUARE: "1 / 1" }[scene_info.video_format] || "16 / 9";
  const previewFrameClass = scene_info.video_format === "PORTRAIT"
    ? "mx-auto h-[min(48vh,360px)] max-w-full aspect-[9/16]"
    : scene_info.video_format === "SQUARE"
      ? "mx-auto aspect-square w-full max-w-[320px]"
      : "aspect-video w-full";
  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title="Edit visual" description="Upload your own media or generate an image from a description." busy={!!busy}>
    <div className="grid gap-6 sm:grid-cols-2">
      <div><p className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">{preview ? "New visual preview" : "Current visual"}</p><div style={{ aspectRatio: scene_info.video_format === "PORTRAIT" ? undefined : previewAspectRatio }} className={`flex items-center justify-center overflow-hidden rounded-xl bg-gray-100 dark:bg-gray-900 ${previewFrameClass}`}>{media ? isVideo ? <video src={media} controls className="h-full w-full object-cover" /> : <img src={media} alt="Scene visual preview" className="h-full w-full object-cover" /> : <p className="text-sm text-gray-400">No visual yet</p>}</div></div>
      <div>
        <div className="mb-4 flex rounded-xl bg-gray-100 p-1 dark:bg-gray-900" aria-label="Visual source">{["upload", "generate"].map(value => <button type="button" key={value} disabled={!!busy} aria-pressed={mode === value} onClick={() => setMode(value)} className={`flex-1 rounded-lg py-2 text-sm font-medium ${mode === value ? "bg-white text-blue-600 shadow-sm dark:bg-gray-700 dark:text-blue-300" : "text-gray-500 dark:text-gray-400"}`}>{value === "upload" ? "Upload media" : "Generate with AI"}</button>)}</div>
        {mode === "upload" ? <><label htmlFor="scene-media" className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Choose an image or video</label><input key={String(showModal)} id="scene-media" type="file" accept="image/*,video/*" disabled={!!busy} onChange={e => setFile(e.target.files[0] || null)} className={`${editorInput} file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:text-blue-700`} /><label className="mt-4 flex items-start gap-2 text-sm text-gray-600 dark:text-gray-300"><input type="checkbox" checked={withAudio} disabled={!!busy} onChange={e => setWithAudio(e.target.checked)} className="mt-1 rounded border-gray-300 text-blue-600" />Keep uploaded video audio</label></> : <><label htmlFor="visual-description" className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Image description</label><textarea id="visual-description" rows={5} className={editorInput} value={description} disabled={!!busy} placeholder="Describe the subject, setting, and style…" onChange={e => setDescription(e.target.value)} /><p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Generating replaces the current scene visual.</p></>}
      </div>
    </div>
    <footer className="mt-6 flex justify-end gap-3"><button type="button" disabled={!!busy} onClick={() => setShowModal(false)} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 dark:text-gray-300">Cancel</button><button type="button" onClick={run} disabled={!!busy || (mode === "upload" ? !file && !scene_info.scene_image_id : !description.trim())} className={editorButton}>{busy ? mode === "upload" ? "Uploading…" : "Generating…" : mode === "upload" ? "Save visual" : "Generate image"}</button></footer>
  </EditorDialog>;
};
