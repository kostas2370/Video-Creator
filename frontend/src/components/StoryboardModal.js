import React, { useEffect, useRef, useState } from "react";
import { Dialog, DialogHeader, DialogBody, DialogFooter } from "@material-tailwind/react";
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
    setScript(JSON.parse(JSON.stringify(video.gpt_answer)));
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
    <Dialog open={open} handler={() => !busy && onClose()} size="xl" className="bg-white dark:bg-gray-800" dismiss={{ escapeKey: !busy, outsidePress: !busy }}>
      <form onSubmit={proceed}>
        <DialogHeader className="text-gray-900 dark:text-white">Review your storyboard</DialogHeader>
        <DialogBody className="max-h-[65vh] overflow-y-auto text-gray-700 dark:text-gray-200">
          <p className="mb-5 text-sm">Review and edit the generated prompts below. Visuals and narration will be created after you press Proceed.</p>
          <label className="block text-sm font-semibold">Video title
            <input autoFocus required maxLength={50} value={script.title} disabled={busy} onChange={event => setScript({ ...script, title: event.target.value })} className={inputClass} />
          </label>
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
                </div>
              ))}
            </section>
          ))}
          {error && <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-300">{error}</p>}
        </DialogBody>
        <DialogFooter className="gap-3 border-t border-gray-200 dark:border-gray-600">
          <button type="button" disabled={busy} onClick={onClose} className="rounded-xl px-4 py-3 text-sm font-semibold text-gray-700 disabled:opacity-50 dark:text-gray-200">Close</button>
          <button type="submit" disabled={busy} className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{busy ? "Starting generation…" : "Proceed"}</button>
        </DialogFooter>
      </form>
    </Dialog>
  );
}
