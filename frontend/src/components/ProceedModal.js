import React from "react";
import { useNavigate } from "react-router-dom";
import { EditorDialog, editorButton } from "./ui/EditorDialog";

export function ProceedModal({ open, setOpen, video_id }) {
  const navigate = useNavigate();
  return <EditorDialog open={open} onClose={() => setOpen(false)} title="Your video is ready!" description="You can now edit or export your video." maxWidth="max-w-lg" footer={<div className="flex justify-end gap-3">
    <button type="button" onClick={() => setOpen(false)} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 dark:text-gray-300">Cancel</button>
    <button type="button" onClick={() => navigate(`/videos/${video_id}`)} className={editorButton}>Open editor</button>
  </div>}>
    <p className="text-sm text-gray-700 dark:text-gray-200">Would you like to go to the editing page?</p>
  </EditorDialog>;
}
