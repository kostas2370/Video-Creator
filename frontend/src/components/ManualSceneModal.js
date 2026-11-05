import { LibraryPicker } from "./LibraryPicker";
import { SceneCreationChoices, SceneMediaUpload, SceneDraftPreview } from "./SceneComposer";
import { RiUpload2Line, RiLayoutLine, RiFolderOpenLine } from "react-icons/ri";
import { useEffect, useState } from "react";
import { createScene } from "../api/apiService";
import { toast } from "react-toastify";
import { EditorDialog, editorInput, editorButton } from "./ui/EditorDialog";
import { ScenePositionPicker } from "./ui/ScenePositionPicker";

export function ManualSceneModal({ id, showModal, setShowModal, setItems, scenes = [], videoFormat = "LANDSCAPE" }) {
  const [library, setLibrary] = useState(false);
  const [mode, setMode] = useState("upload");
  const [file, setFile] = useState(null), [text, setText] = useState("");
  const [duration, setDuration] = useState(""), [position, setPosition] = useState("");
  const [withAudio, setWithAudio] = useState(true);
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  useEffect(() => { if (showModal) { setFile(null); setText(""); setDuration(""); setPosition(""); setWithAudio(true); setError(""); setMode("upload"); setLibrary(false); } }, [showModal, id]);
  const save = async event => {
    event.preventDefault();
    if (busy || (mode === "upload" && !file)) return;
    setBusy(true); setError("");
    try {
      const data = new FormData();
      if (mode === "upload" && file) data.append("image", file);
      data.append("text", text.trim()); data.append("with_audio", mode === "upload" && withAudio);
      if (duration !== "") data.append("duration", duration);
      if (position) data.append("position", position);
      const response = await createScene(id, data);
      if (!response.ok) throw new Error(response.message || "Could not add the scene. Try again.");
      toast.success("Scene added"); setItems(); setShowModal(false);
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  };
  const selectedIndex = scenes.findIndex(scene => String(scene.position) === position);
  const placement = position && selectedIndex >= 0 ? `Before scene ${selectedIndex + 1}` : scenes.length ? "At the end of your story" : "Start your story";
  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title="Add a scene" description="Bring your own media, or start with a blank canvas for text and a voiceover." maxWidth="max-w-5xl" panelClassName="scene-composer-dialog" busy={busy} footer={<div className="flex flex-wrap items-center justify-between gap-3"><div className="hidden sm:block"><p className="text-sm font-semibold">{mode === "upload" ? "Your media" : "Blank scene"}</p><p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{placement}</p></div><div className="ml-auto flex gap-2"><button type="button" disabled={busy} onClick={() => setShowModal(false)} className="rounded-xl px-4 py-3 text-sm text-gray-500 dark:text-gray-300">Cancel</button><button type="submit" form="manual-scene" disabled={busy || (mode === "upload" && !file)} className={editorButton}>{busy ? "Adding…" : mode === "blank" ? "Add blank scene" : "Add scene"}</button></div></div>}>
    <LibraryPicker open={library} onClose={() => setLibrary(false)} videoId={id} purpose="new_scene" onSaved={() => { setLibrary(false); setItems(); setShowModal(false); }} sceneData={{ text: text.trim(), with_audio: withAudio, ...(duration !== "" ? { duration: Number(duration) } : {}), ...(position ? { position: Number(position) } : {}) }} />
    <form id="manual-scene" onSubmit={save}><fieldset disabled={busy} className="grid min-w-0 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
      <div className="min-w-0 space-y-6">
        <SceneCreationChoices label="Scene source" value={mode} onChange={value => { setMode(value); setError(""); }} choices={[
          { value: "upload", label: "Upload media", detail: "Use a photo or video clip", icon: RiUpload2Line },
          { value: "blank", label: "Blank canvas", detail: "Start with words and a voiceover", icon: RiLayoutLine },
        ]} />
        {mode === "upload" ? <section aria-label="Scene media" className="space-y-3">
          <SceneMediaUpload inputId="manual-media" file={file} onChange={setFile} onError={setError} disabled={busy} />
          <button type="button" onClick={() => setLibrary(true)} className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-gray-200 px-4 py-3 text-sm font-semibold text-blue-600 hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-700 dark:text-blue-300 dark:hover:bg-gray-900"><RiFolderOpenLine aria-hidden="true" className="h-4 w-4" />Choose from media library</button>
          <p className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">Use your own images or clips. Videos can be up to 15 minutes long.</p>
        </section> : <div className="rounded-2xl border border-blue-100 bg-blue-50/60 p-4 text-sm leading-relaxed text-blue-800 dark:border-blue-900 dark:bg-blue-950/20 dark:text-blue-200">Start with an empty scene. Add captions below, then record a voiceover or add visuals in the editor.</div>}
        <div><label className="block text-sm font-semibold" htmlFor="manual-caption">Caption text <span className="font-normal text-gray-400">(optional)</span></label><textarea id="manual-caption" rows={4} maxLength={2000} value={text} onChange={event => setText(event.target.value)} className={`${editorInput} mt-2 resize-y leading-relaxed`} placeholder="Give this moment a few words…" /><p className="mt-2 text-right text-xs text-gray-500">{text.length}/2,000</p></div>
        <div className="rounded-2xl border border-gray-200 p-4 dark:border-gray-700"><label className="block text-sm font-semibold" htmlFor="manual-duration">Scene duration <span className="font-normal text-gray-400">(seconds)</span><input id="manual-duration" type="number" min="0.1" max="900" step="0.1" value={duration} onChange={event => setDuration(event.target.value)} className={`${editorInput} mt-2`} placeholder="Automatic" /></label><p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Automatic uses the clip or voice length, or 5 seconds for a photo. Shorter trims the end; longer holds the final frame.</p>{mode === "upload" && <label className="mt-4 flex items-center gap-2 border-t border-gray-100 pt-4 text-sm dark:border-gray-700"><input type="checkbox" checked={withAudio} onChange={event => setWithAudio(event.target.checked)} className="accent-blue-600" />Keep the video clip’s sound</label>}</div>
      </div>
      <aside className="min-w-0 space-y-4 lg:sticky lg:top-0">
        <SceneDraftPreview manual file={mode === "upload" ? file : null} text={text} duration={duration} videoFormat={videoFormat} />
        <ScenePositionPicker compact scenes={scenes} value={position} onChange={setPosition} disabled={busy} />
        <p className="px-1 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Your scene stays editable. Fine-tune audio, captions and timing in the editor.</p>
      </aside>
    </fieldset>{error && <p role="alert" className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">{error}</p>}</form>
  </EditorDialog>;
}
