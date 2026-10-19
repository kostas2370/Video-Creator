import { useEffect, useState } from "react";
import { MediaLibrary } from "./MediaLibrary";
import { EditorDialog } from "./ui/EditorDialog";
import { useMediaAsset } from "../api/apiService";

export function LibraryPicker({ open, onClose, videoId, sceneId, purpose = "visual", onSaved, sceneData = {} }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  useEffect(() => { if (open) setError(""); }, [open, videoId, sceneId]);
  const use = async asset => {
    if (busy) return;
    setBusy(true); setError("");
    const response = await useMediaAsset(asset.id, { video_id: videoId, scene_id: sceneId, purpose, ...sceneData });
    if (response.ok) { onSaved(); onClose(); } else setError(response.message || "Could not reuse this file.");
    setBusy(false);
  };
  return <EditorDialog open={open} onClose={onClose} busy={busy} title="Choose from your media library" description={purpose === "music" ? "Reuse a saved audio track as background music." : "Choose a saved image or clip for this scene."} maxWidth="max-w-5xl" footer={<div className="flex justify-end"><button type="button" disabled={busy} onClick={onClose} className="px-4 py-2 text-sm text-gray-500">Cancel</button></div>}>
    {error && <p role="alert" className="mb-4 text-sm text-red-600 dark:text-red-300">{error}</p>}
    {open && <MediaLibrary kind={purpose === "music" ? "AUDIO" : "VISUAL"} onSelect={use} selecting={busy} />}
  </EditorDialog>;
}
