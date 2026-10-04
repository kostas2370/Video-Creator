import React, { useEffect, useState } from "react";
import { updateScene, generateScene } from "../api/apiService";
import { toast } from "react-toastify";
import { EditorDialog, editorInput, editorButton } from "./ui/EditorDialog";

export const EditSceneModal = ({ showModal, setShowModal, scene_info, setUpdate }) => {
  const [sceneText, setSceneText] = useState("");
  const [promptText, setPromptText] = useState("");
  const [busy, setBusy] = useState("");
  useEffect(() => {
    if (showModal) { setSceneText(scene_info.dialogue || ""); setPromptText(""); }
  }, [showModal, scene_info.id, scene_info.dialogue]);

  const run = async (action) => {
    setBusy(action);
    try {
      if (action === "save") {
        const { data: response } = await updateScene(scene_info.id, { text: sceneText });
        if (response) {
          if (response.narration_status === "missing") toast.warning("Dialogue saved, but narration is unavailable. Retry audio in the scene.");
          else toast.success("Scene updated successfully");
          setUpdate(true); setShowModal(false);
        }
      } else {
        const { data: response } = await generateScene(scene_info.id, { text: promptText });
        if (response) setSceneText(response.text);
      }
    } catch { toast.error("Could not update the scene. Please try again."); }
    finally { setBusy(""); }
  };
  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title="Edit dialogue" description="Adjust the words or use AI to draft a rewrite. Review your changes before saving." busy={!!busy}>
    <label htmlFor="scene-dialogue" className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Dialogue</label>
    <textarea id="scene-dialogue" rows={6} className={editorInput} value={sceneText} disabled={!!busy} onChange={e => setSceneText(e.target.value)} />
    <div className="mt-5 rounded-xl border border-blue-100 bg-blue-50/50 p-4 dark:border-gray-700 dark:bg-gray-900/30">
      <label htmlFor="rewrite-prompt" className="mb-1 block text-sm font-semibold text-gray-800 dark:text-gray-200">Rewrite with AI</label>
      <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">Describe the tone, length, or changes you have in mind.</p>
      <textarea id="rewrite-prompt" rows={2} className={editorInput} placeholder="Make it shorter and more conversational…" value={promptText} disabled={!!busy} onChange={e => setPromptText(e.target.value)} />
      <button type="button" onClick={() => run("rewrite")} disabled={!!busy || !promptText.trim()} className="mt-3 rounded-lg px-3 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-100 disabled:opacity-40 dark:text-blue-400 dark:hover:bg-gray-700">{busy === "rewrite" ? "Rewriting…" : "Generate rewrite"}</button>
    </div>
    <footer className="mt-6 flex justify-end gap-3"><button type="button" disabled={!!busy} onClick={() => setShowModal(false)} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 dark:text-gray-300">Cancel</button><button type="button" disabled={!!busy || !sceneText.trim()} onClick={() => run("save")} className={editorButton}>{busy === "save" ? "Saving…" : "Save dialogue"}</button></footer>
  </EditorDialog>;
};
