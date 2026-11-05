import React, { useState } from "react";
import { toast } from "react-toastify";
import { HiOutlineBookmark } from "react-icons/hi2";
import { createTemplate } from "../api/apiService";
import { EditorDialog, editorInput, editorButton, editorSecondaryButton } from "./ui/EditorDialog";

export const SaveTemplateModal = ({
  showModal,
  setShowModal,
  settings,
  onSaved,
}) => {
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event) => {
    event.preventDefault();
    if (loading) return;

    if (title.trim() === "") {
      toast.error("Give the template a name first!");
      return;
    }

    setLoading(true);
    try {
      const response = await createTemplate({ ...settings, title: title.trim() });
      if (!response.ok) { toast.error(response.message); return; }
      toast.success(`Saved "${response.data.title}" as a template`);
      setTitle("");
      setShowModal(false);
      onSaved?.(response.data);
    } catch { toast.error("Could not save your template. Please try again."); }
    finally { setLoading(false); }
  };

  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title="Save as template" description="Keep this setup ready for your next video." icon={HiOutlineBookmark} busy={loading} maxWidth="max-w-lg" footer={<div className="flex justify-end gap-2">
    <button type="button" disabled={loading} onClick={() => setShowModal(false)} className={editorSecondaryButton}>Cancel</button><button type="submit" form="save-template-form" disabled={loading || !title.trim()} className={editorButton}>{loading ? "Saving…" : "Save template"}</button>
  </div>}>
    <form id="save-template-form" onSubmit={onSubmit} className="space-y-5"><label htmlFor="template_title" className="block text-sm font-semibold">Template name<input id="template_title" name="template_title" required maxLength={50} value={title} disabled={loading} className={`${editorInput} mt-3`} placeholder="Shorts about cats" onChange={event => setTitle(event.target.value)} /></label><p className="text-sm leading-relaxed text-gray-500 dark:text-gray-400">Saves the prompt and all creation settings so you can use the same setup again.</p></form>
  </EditorDialog>;
};
