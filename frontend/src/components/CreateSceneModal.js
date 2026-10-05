import React, { useEffect, useState } from "react";
import { createScene, draftScene } from "../api/apiService";
import { toast } from "react-toastify";
import { EditorDialog, editorInput, editorButton } from "./ui/EditorDialog";

export const SceneCreationModal = ({ id, showModal, setShowModal, setItems }) => {
  const [text, setText] = useState("");
  const [imageDescription, setImageDescription] = useState("");
  const [image, setImage] = useState(null);
  const [isLast, setIsLast] = useState(false);
  const [withAudio, setWithAudio] = useState(false);
  const [mode, setMode] = useState("manual");
  const [prompt, setPrompt] = useState("");
  const [useContext, setUseContext] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (showModal) {
      setText(""); setImageDescription(""); setImage(null); setIsLast(false);
      setWithAudio(false); setMode("manual"); setPrompt(""); setUseContext(true); setError("");
    }
  }, [showModal, id]);

  const generate = async () => {
    setBusy("draft"); setError("");
    try {
      const response = await draftScene(id, { prompt: prompt.trim(), use_context: useContext });
      if (!response.data) { setError(response.message || "Could not generate a draft. Please try again."); return; }
      setText(response.data.text); setImageDescription(response.data.image_description);
      toast.success("Draft ready. Review and edit it before adding the scene.");
    } catch { setError("Could not generate a draft. Please try again."); }
    finally { setBusy(""); }
  };

  const onSubmit = async event => {
    event.preventDefault();
    if (busy || !text.trim()) return;
    setBusy("save"); setError("");
    const data = new FormData();
    data.append("text", text.trim());
    if (imageDescription.trim()) data.append("image_description", imageDescription.trim());
    if (image) data.append("image", image);
    data.append("is_last", isLast);
    data.append("with_audio", withAudio);
    try {
      const response = await createScene(id, data);
      if (!response.data) { setError(response.message || "Could not add the scene. Please try again."); return; }
      toast.success("Scene queued. You can keep working while it is created."); setItems(true); setShowModal(false);
    } catch { setError("Could not add the scene. Please try again."); }
    finally { setBusy(""); }
  };

  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title="Add a scene" description="Write the next moment yourself or start with an AI draft. Review everything before adding it to your video." busy={!!busy}>
    <form onSubmit={onSubmit}>
      <fieldset disabled={!!busy} className="space-y-5">
        <div className="flex gap-2 rounded-xl bg-gray-100 p-1 dark:bg-gray-900" aria-label="Creation mode">
          {[["manual", "Write manually"], ["ai", "Create with AI"]].map(([value, label]) => <button key={value} type="button" aria-pressed={mode === value} onClick={() => setMode(value)} className={`flex-1 rounded-lg px-4 py-2.5 text-sm font-semibold ${mode === value ? "bg-white text-blue-600 shadow-sm dark:bg-gray-700 dark:text-blue-300" : "text-gray-500 dark:text-gray-400"}`}>{label}</button>)}
        </div>
        {mode === "ai" && <section className="space-y-3 rounded-xl border border-blue-100 bg-blue-50/50 p-4 dark:border-gray-700 dark:bg-gray-900/30">
          <label htmlFor="new-scene-prompt" className="block text-sm font-semibold text-gray-800 dark:text-gray-200">What should happen in this scene?</label>
          <textarea id="new-scene-prompt" rows={3} maxLength={2000} className={editorInput} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Introduce a surprising discovery, with a curious, conversational tone…" />
          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-200">Scenario context</legend>
            {[[true, "With context", "Send the title and every current scene, including dialogue and visual descriptions, to AI."], [false, "No context", "Send only your instructions above. No existing scenario content is included."]].map(([value, label, detail]) => <label key={label} className={`cursor-pointer rounded-xl border p-3 ${useContext === value ? "border-blue-500 bg-white dark:bg-gray-800" : "border-gray-200 dark:border-gray-600"}`}>
              <span className="flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-gray-100"><input type="radio" name="scene-context" checked={useContext === value} onChange={() => setUseContext(value)} />{label}</span>
              <span className="mt-2 block text-xs leading-relaxed text-gray-500 dark:text-gray-400">{detail}</span>
            </label>)}
          </fieldset>
          <button type="button" disabled={!!busy || !prompt.trim()} onClick={generate} className={editorButton}>{busy === "draft" ? "Drafting scene…" : "Generate draft"}</button>
          <p className="text-xs text-gray-500 dark:text-gray-400">Generating a draft replaces the dialogue and visual description below.</p>
        </section>}
        <div>
          <label htmlFor="new-scene-text" className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Dialogue</label>
          <textarea id="new-scene-text" rows={4} required className={editorInput} value={text} onChange={e => setText(e.target.value)} placeholder="What will the narrator say?" />
        </div>
        <div>
          <label htmlFor="new-scene-visual" className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Visual description <span className="font-normal text-gray-400">(optional)</span></label>
          <textarea id="new-scene-visual" rows={3} className={editorInput} value={imageDescription} onChange={e => setImageDescription(e.target.value)} placeholder="Describe the setting, subject, lighting, and camera angle…" />
        </div>
        <div className="rounded-xl border border-dashed border-gray-300 p-4 dark:border-gray-600">
          <label htmlFor="new-scene-file" className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Upload a visual <span className="font-normal text-gray-400">(optional)</span></label>
          <input id="new-scene-file" type="file" accept="image/*,video/*" className="block w-full text-sm text-gray-500 dark:text-gray-300" onChange={e => setImage(e.target.files[0] || null)} />
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">An uploaded image or clip is used instead of generating a visual from the description.</p>
        </div>
        <div className="flex flex-wrap gap-5 text-sm text-gray-700 dark:text-gray-200">
          <label className="flex items-center gap-2"><input type="checkbox" checked={withAudio} onChange={e => setWithAudio(e.target.checked)} />Keep visual audio</label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={isLast} onChange={e => setIsLast(e.target.checked)} />End of scene group</label>
        </div>
      </fieldset>
      {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">{error}</p>}
      <footer className="mt-6 flex justify-end gap-3 border-t border-gray-100 pt-5 dark:border-gray-700">
        <button type="button" disabled={!!busy} onClick={() => setShowModal(false)} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 dark:text-gray-300">Cancel</button>
        <button type="submit" disabled={!!busy || !text.trim()} className={editorButton}>{busy === "save" ? "Queueing scene…" : "Add scene"}</button>
      </footer>
    </form>
  </EditorDialog>;
};
