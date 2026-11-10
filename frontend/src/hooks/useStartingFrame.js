import { useEffect, useState } from "react";
import { toast } from "react-toastify";
import { generateSceneImage, updateStartingFrame } from "../api/apiService";

async function sendStartingFrameAction(scene, operation, description, file) {
  const data = new FormData();
  if (operation === "prepare" || operation === "retry") {
    data.append("image_description", description);
    return generateSceneImage(scene.id, data);
  }
  data.append("operation", operation);
  if (scene.starting_asset) data.append("asset_id", scene.starting_asset);
  if (operation === "upload") {
    data.append("image", file);
    data.append("image_description", description);
  }
  return updateStartingFrame(scene.id, data);
}

export function useStartingFrame(scene, { disabled, onSaved }) {
  const savedDescription = scene.starting_frame_description || scene.scene_image?.prompt || "";
  const [description, setDescription] = useState(savedDescription);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    setDescription(savedDescription);
    setFile(null);
  }, [scene.id, scene.starting_asset, savedDescription]);

  const edited = description.trim() !== (scene.starting_frame_description || "").trim();
  const blocked = disabled || !!busy;
  const run = async operation => {
    if (blocked) return;
    setBusy(operation);
    setError("");
    try {
      const response = await sendStartingFrameAction(scene, operation, description, file);
      if (!response?.ok) {
        setError(response?.message || "Could not finish this step. Your saved media is preserved.");
        return;
      }
      if (operation === "upload") {
        setFile(null);
        toast.success("Starting frame ready for review");
      }
      if (operation === "approve") toast.success("Starting frame approved");
    } catch {
      setError("Could not finish this step. Your saved media is preserved.");
    } finally {
      setBusy("");
      onSaved(true);
    }
  };

  return { description, setDescription, file, setFile, busy, error, edited, blocked, run };
}
