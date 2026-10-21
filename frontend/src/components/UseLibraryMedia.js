import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAssetOptions } from "../hooks/useAssetOptions";
import { getVideos, useMediaAsset } from "../api/apiService";
import { MoreAssetOptions } from "./ui/MoreAssetOptions";
import { EditorDialog, editorButton, editorInput } from "./ui/EditorDialog";

const descriptions = {
  music: "Replaces the project's background music.",
  cover: "Uses this image as the video’s cover.",
  new_scene: "Adds a new scene at the end of the project.",
};

export function UseLibraryMedia({ asset, onClose }) {
  const videos = useAssetOptions(getVideos);
  const [video, setVideo] = useState(""), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const navigate = useNavigate();
  const [purpose, setPurpose] = useState("new_scene");
  const usePurpose = asset.kind === "AUDIO" ? "music" : purpose;
  const use = async () => {
    setBusy(true); setError("");
    const response = await useMediaAsset(asset.id, { video_id: video, purpose: usePurpose, with_audio: asset.kind === "VIDEO" });
    if (response.ok) { onClose(); navigate(`/videos/${video}/`); } else setError(response.message);
    setBusy(false);
  };
  return <EditorDialog open onClose={onClose} busy={busy} title="Use media in a video" description={`${asset.title} · ${descriptions[usePurpose]}`} maxWidth="max-w-lg" footer={<div className="flex justify-end gap-2"><button type="button" disabled={busy} onClick={onClose} className="px-4 py-3 text-sm text-gray-500">Cancel</button><button type="button" disabled={!video || busy} onClick={use} className={editorButton}>{busy ? "Adding…" : "Use in video"}</button></div>}>
    {asset.kind === "IMAGE" && <label className="mb-4 block text-sm">Use image as<select value={purpose} disabled={busy} onChange={event => setPurpose(event.target.value)} className={`${editorInput} mt-2`}><option value="new_scene">A new scene</option><option value="cover">Video cover</option></select></label>}
    <label className="block text-sm">Choose a video<select disabled={busy} value={video} onChange={event => setVideo(event.target.value)} className={`${editorInput} mt-2`}><option value="">{videos.loading ? "Loading videos…" : "Choose a project"}</option>{videos.items.map(item => <option key={item.id} value={item.id} disabled={!["READY", "COMPLETED", "FAILED"].includes(item.status)}>{item.title}{!["READY", "COMPLETED", "FAILED"].includes(item.status) ? " · Processing" : ""}</option>)}</select></label>
    <MoreAssetOptions options={videos} label="videos" />
    {!videos.loading && !videos.failed && !videos.items.length && <p className="mt-3 text-sm text-gray-500">Create a video project first, then reuse media here.</p>}
    {error && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-300">{error}</p>}
  </EditorDialog>;
}
