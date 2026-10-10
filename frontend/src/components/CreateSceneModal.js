import React, { useEffect, useState } from "react";
import { createScene, draftScene } from "../api/apiService";
import { toast } from "react-toastify";
import { RiEditLine, RiSparklingLine, RiVolumeUpLine, RiImageLine, RiUpload2Line, RiSettings3Line } from "react-icons/ri";
import { ScenePositionPicker } from "./ui/ScenePositionPicker";
import { EditorDialog, editorInput, editorButton } from "./ui/EditorDialog";

export const SceneCreationModal = ({ id, showModal, setShowModal, setItems, scenes = [] }) => {
  const [position, setPosition] = useState("");
  const [text, setText] = useState("");
  const [imageDescription, setImageDescription] = useState("");
  const [image, setImage] = useState(null);
  const [isLast, setIsLast] = useState(false);
  const [withAudio, setWithAudio] = useState(false);
  const [mode, setMode] = useState("manual");
  const [prompt, setPrompt] = useState("");
  const [useContext, setUseContext] = useState(true);
  const [draftType, setDraftType] = useState("sentence");
  const [sentenceCount, setSentenceCount] = useState(1);
  const [drafts, setDrafts] = useState([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (showModal) {
      setPosition(""); setText(""); setImageDescription(""); setImage(null); setIsLast(false);
      setWithAudio(false); setMode("manual"); setPrompt(""); setUseContext(true); setError("");
      setDraftType("sentence"); setSentenceCount(1); setDrafts([]);
    }
  }, [showModal, id]);

  const generate = async () => {
    setBusy("draft"); setError("");
    try {
      const response = await draftScene(id, { prompt: prompt.trim(), use_context: useContext, draft_type: draftType, sentence_count: Number(sentenceCount) });
      if (!response.data) { setError(response.message || "Could not generate a draft. Please try again."); return; }
      if (response.data.scenes) {
        setDrafts(response.data.scenes); setText(""); setImageDescription(""); setImage(null);
      } else {
        setDrafts([]); setText(response.data.text); setImageDescription(response.data.image_description);
      }
      toast.success("Draft ready. Review each sentence before adding it.");
    } catch { setError("Could not generate a draft. Please try again."); }
    finally { setBusy(""); }
  };

  const onSubmit = async event => {
    event.preventDefault();
    if (busy || (drafts.length ? drafts.some(item => !item.text.trim()) : !text.trim())) return;
    setBusy("save"); setError("");
    let data;
    if (drafts.length) {
      data = { ...(position ? { position: Number(position) } : {}), scenes: drafts.map((item, index) => ({
        text: item.text.trim(),
        ...(item.image_description.trim() ? { image_description: item.image_description.trim() } : {}),
        is_last: index === drafts.length - 1, with_audio: withAudio,
      })) };
    } else {
      data = new FormData();
      data.append("text", text.trim());
      if (position) data.append("position", position);
      if (imageDescription.trim()) data.append("image_description", imageDescription.trim());
      if (image) data.append("image", image);
      data.append("is_last", isLast);
      data.append("with_audio", withAudio);
    }
    try {
      const response = await createScene(id, data);
      if (!response.data) { setError(response.message || "Could not add the scene. Please try again."); return; }
      toast.success("Scenes queued. You can keep working while they are created."); setItems(true); setShowModal(false);
    } catch { setError("Could not add the scene. Please try again."); }
    finally { setBusy(""); }
  };

  const updateDraft = (index, field, value) => setDrafts(items => items.map((item, position) => position === index ? { ...item, [field]: value } : item));
  const canSubmit = drafts.length ? drafts.every(item => item.text.trim()) : !!text.trim();
  const selectedIndex = scenes.findIndex(scene => String(scene.position) === position);
  const placement = position && selectedIndex >= 0 ? `Before scene ${selectedIndex + 1}` : scenes.length ? "At the end of your story" : "Start your story";
  useEffect(() => {
    if (position && !scenes.some(scene => String(scene.position) === position)) setPosition("");
  }, [position, scenes]);

  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title="Add a scene" description="Shape a new moment. Choose its place, write the dialogue, and bring it to life." busy={!!busy} footer={
    <footer className="flex items-center justify-between gap-3">
      <div className="hidden min-w-0 sm:block"><p className="text-sm font-semibold text-gray-800 dark:text-gray-100">{drafts.length > 1 ? `${drafts.length} scenes` : "1 scene"}</p><p className="mt-0.5 truncate text-xs text-gray-400">{placement}</p></div>
      <div className="flex w-full justify-end gap-2 sm:w-auto">
        <button type="button" disabled={!!busy} onClick={() => setShowModal(false)} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700">Cancel</button>
        <button type="submit" form="create-scene-form" disabled={!!busy || !canSubmit} className={editorButton}>{busy === "save" ? "Adding…" : drafts.length > 1 ? `${position ? "Insert" : "Add"} ${drafts.length} scenes` : position ? "Insert scene" : "Add scene"}</button>
      </div>
    </footer>
  }>
    <form id="create-scene-form" onSubmit={onSubmit}>
      <fieldset disabled={!!busy} className="min-w-0 space-y-6">
        <ScenePositionPicker disabled={!!busy} scenes={scenes} value={position} onChange={setPosition} count={drafts.length || 1} />
        <div className="grid grid-cols-2 gap-3" aria-label="Creation mode">
          {[["manual", "Write it yourself", "Your words, your story", RiEditLine], ["ai", "Create with AI", "Turn an idea into scenes", RiSparklingLine]].map(([value, label, detail, Icon]) => <button key={value} type="button" aria-pressed={mode === value} onClick={() => setMode(value)} className={`flex items-start gap-3 rounded-xl border p-3.5 text-left transition ${mode === value ? "border-blue-500 bg-blue-50/60 ring-1 ring-blue-500 dark:bg-blue-900/20" : "border-gray-200 hover:border-gray-300 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"}`}>
            <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${mode === value ? "text-blue-600 dark:text-blue-300" : "text-gray-400"}`} /><span><span className="block text-sm font-semibold text-gray-900 dark:text-white">{label}</span><span className="mt-1 hidden text-xs text-gray-400 sm:block">{detail}</span></span>
          </button>)}
        </div>
        {mode === "ai" && <section className="space-y-3 rounded-xl border border-blue-100 bg-blue-50/50 p-4 dark:border-gray-700 dark:bg-gray-900/30">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm font-semibold text-gray-800 dark:text-gray-200" htmlFor="draft-type">Draft length
              <select id="draft-type" className={editorInput} value={draftType} onChange={event => { const value = event.target.value; setDraftType(value); setSentenceCount(value === "sentence" ? 1 : value === "section" ? 3 : 6); }}>
                <option value="sentence">One sentence</option><option value="section">A section</option><option value="story">A short story</option>
              </select>
            </label>
            <label className="block text-sm font-semibold text-gray-800 dark:text-gray-200" htmlFor="draft-count">Sentences / scenes
              <input id="draft-count" type="number" min={1} max={12} disabled={draftType === "sentence"} required className={editorInput} value={sentenceCount} onChange={event => setSentenceCount(event.target.value)} />
            </label>
          </div>
          <label htmlFor="new-scene-prompt" className="block text-sm font-semibold text-gray-800 dark:text-gray-200">What should happen in this scene?</label>
          <textarea id="new-scene-prompt" rows={3} maxLength={2000} className={editorInput} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Introduce a surprising discovery, with a curious, conversational tone…" />
          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-200">Scenario context</legend>
            {[[true, "With context", "Send the title and every current scene, including dialogue and visual descriptions, to AI."], [false, "No context", "Send only your instructions above. No existing scenario content is included."]].map(([value, label, detail]) => <label key={label} className={`cursor-pointer rounded-xl border p-3 ${useContext === value ? "border-blue-500 bg-white dark:bg-gray-800" : "border-gray-200 dark:border-gray-600"}`}>
              <span className="flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-gray-100"><input type="radio" name="scene-context" checked={useContext === value} onChange={() => setUseContext(value)} />{label}</span>
              <span className="mt-2 block text-xs leading-relaxed text-gray-500 dark:text-gray-400">{detail}</span>
            </label>)}
          </fieldset>
          <button type="button" disabled={!!busy || !prompt.trim() || !Number.isInteger(Number(sentenceCount)) || Number(sentenceCount) < 1 || Number(sentenceCount) > 12} onClick={generate} className={editorButton}>{busy === "draft" ? "Drafting…" : "Generate draft"}</button>
          <p className="text-xs text-gray-500 dark:text-gray-400">Generating a draft replaces the dialogue and visual description below.</p>
        </section>}
        {drafts.length > 0 ? <section className="space-y-4" aria-label="Draft sentences">
          <p className="text-sm text-gray-500 dark:text-gray-400">Review {drafts.length} scenes. Edit or remove any sentence before adding them.</p>
          {drafts.map((item, index) => <div key={index} className="space-y-3 rounded-xl border border-gray-200 p-4 dark:border-gray-600">
            <div className="flex items-center justify-between"><h3 className="text-sm font-semibold">Scene {index + 1}</h3><button type="button" disabled={drafts.length === 1} onClick={() => setDrafts(items => items.filter((_, position) => position !== index))} className="text-xs text-red-600 disabled:opacity-40">Remove</button></div>
            <label htmlFor={`draft-text-${index}`} className="block text-sm">Sentence</label>
            <textarea id={`draft-text-${index}`} rows={2} required maxLength={320} className={editorInput} value={item.text} onChange={event => updateDraft(index, "text", event.target.value)} />
            <label htmlFor={`draft-visual-${index}`} className="block text-sm">Visual description</label>
            <textarea id={`draft-visual-${index}`} rows={2} maxLength={600} className={editorInput} value={item.image_description} onChange={event => updateDraft(index, "image_description", event.target.value)} />
          </div>)}
        </section> : <>
        <div>
          <label htmlFor="new-scene-text" className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-200"><RiVolumeUpLine className="text-gray-400" />Dialogue</label>
          <textarea id="new-scene-text" rows={3} required className={editorInput} value={text} onChange={e => setText(e.target.value)} placeholder="What will the narrator say?" />
        </div>
        <div>
          <label htmlFor="new-scene-visual" className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-200"><RiImageLine className="text-gray-400" />Visual description <span className="font-normal text-gray-400">(optional)</span></label>
          <textarea id="new-scene-visual" rows={3} className={editorInput} value={imageDescription} onChange={e => setImageDescription(e.target.value)} placeholder="Describe the setting, subject, lighting, and camera angle…" />
        </div>
        <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50/50 p-4 dark:border-gray-600 dark:bg-gray-900/20">
          <label htmlFor="new-scene-file" className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-200"><RiUpload2Line className="text-gray-400" />Upload a visual <span className="font-normal text-gray-400">(optional)</span></label>
          <input id="new-scene-file" type="file" accept="image/*,video/*" className="block w-full text-sm text-gray-500 dark:text-gray-300" onChange={e => setImage(e.target.files[0] || null)} />
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">An uploaded image or clip is used instead of generating a visual from the description.</p>
        </div>
        </>}
        <details className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"><summary className="flex cursor-pointer items-center gap-2 text-sm font-medium text-gray-600 dark:text-gray-300"><RiSettings3Line className="text-gray-400" />More options</summary><div className="mt-4 flex flex-wrap gap-5 text-sm text-gray-700 dark:text-gray-200">
          <label className="flex items-center gap-2"><input type="checkbox" checked={withAudio} onChange={e => setWithAudio(e.target.checked)} />Keep visual audio</label>
          {!drafts.length && <label className="flex items-center gap-2"><input type="checkbox" checked={isLast} onChange={e => setIsLast(e.target.checked)} />End of scene group</label>}
        </div></details>
      </fieldset>
      {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">{error}</p>}
    </form>
  </EditorDialog>;
};
