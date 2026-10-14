import { useObjectUrl } from "../hooks/useObjectUrl";
import { isVideo } from "../utils/media";
import { useEffect, useState } from "react";
import { createScene } from "../api/apiService";
import { toast } from "react-toastify";
import { EditorDialog, editorInput, editorButton } from "./ui/EditorDialog";
import { ScenePositionPicker } from "./ui/ScenePositionPicker";

export function ManualSceneModal({ id, showModal, setShowModal, setItems, scenes = [] }) {
  const [file, setFile] = useState(null), [text, setText] = useState("");
  const [duration, setDuration] = useState(""), [position, setPosition] = useState("");
  const [withAudio, setWithAudio] = useState(true);
  const preview = useObjectUrl(file);
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  useEffect(() => { if (showModal) { setFile(null); setText(""); setDuration(""); setPosition(""); setWithAudio(true); setError(""); } }, [showModal, id]);
  const save = async event => {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError("");
    try {
      const data = new FormData();
      if (file) data.append("image", file);
      data.append("text", text.trim()); data.append("with_audio", withAudio);
      if (duration !== "") data.append("duration", duration);
      if (position) data.append("position", position);
      const response = await createScene(id, data);
      if (!response.ok) throw new Error(response.message || "Could not add the scene. Try again.");
      toast.success("Scene added"); setItems(); setShowModal(false);
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  };
  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title="Add your media" description="Upload a photo or clip, or start with a blank scene for captions and a voiceover." busy={busy} footer={<div className="flex justify-end gap-2"><button type="button" disabled={busy} onClick={() => setShowModal(false)} className="rounded-xl px-4 py-3 text-sm text-gray-500">Cancel</button><button type="submit" form="manual-scene" disabled={busy} className={editorButton}>{busy ? "Adding…" : "Add scene"}</button></div>}>
    <form id="manual-scene" onSubmit={save}><fieldset disabled={busy} className="space-y-5">
      <ScenePositionPicker scenes={scenes} value={position} onChange={setPosition} disabled={busy} />
      <label className="block text-sm font-semibold" htmlFor="manual-media">Photo or video<input key={String(showModal)} id="manual-media" type="file" accept=".jpg,.jpeg,.png,.webp,.mp4,.mov,.webm,.avi,.m4v" className={`${editorInput} mt-2`} onChange={event => setFile(event.target.files[0] || null)} /></label>
      {preview && (isVideo(file) ? <video controls src={preview} className="max-h-60 w-full rounded-xl bg-black" /> : <img src={preview} alt="New scene" className="max-h-60 w-full rounded-xl object-contain" />)}
      <p className="text-xs text-gray-500">Up to 100 MB per file. Video clips can be up to 15 minutes long.</p>
      <label className="block text-sm font-semibold" htmlFor="manual-caption">Caption text (optional)<textarea id="manual-caption" rows={3} maxLength={2000} value={text} onChange={event => setText(event.target.value)} className={`${editorInput} mt-2`} placeholder="Text to display in this scene" /></label>
      <label className="block text-sm font-semibold" htmlFor="manual-duration">Scene duration (seconds)<input id="manual-duration" type="number" min="0.1" max="900" step="0.1" value={duration} onChange={event => setDuration(event.target.value)} className={`${editorInput} mt-2`} placeholder="Automatic" /><span className="mt-2 block text-xs font-normal text-gray-500">Leave empty to use the clip or voice length, or 5 seconds for a photo. A shorter duration trims the end; a longer one holds the final frame.</span></label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={withAudio} onChange={event => setWithAudio(event.target.checked)} />Keep the video clip’s sound</label>
      {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    </fieldset></form>
  </EditorDialog>;
}
