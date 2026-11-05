import React from "react";
import { HiOutlineTrash } from "react-icons/hi2";
import { EditorDialog, editorDangerButton, editorSecondaryButton } from "./ui/EditorDialog";

export function ClearApiKeysModal({ showModal, setShowModal, onConfirm, isClearing }) {
  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title="Remove saved API keys?" description="This removes every API key you have saved in Viddie." icon={HiOutlineTrash} tone="danger" busy={isClearing} maxWidth="max-w-lg" footer={<div className="flex justify-end gap-2">
    <button type="button" disabled={isClearing} onClick={() => setShowModal(false)} className={editorSecondaryButton}>Keep keys</button><button type="button" disabled={isClearing} onClick={onConfirm} className={editorDangerButton}>{isClearing ? "Removing…" : "Remove all keys"}</button>
  </div>}>
    <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm leading-relaxed text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200">This cannot be undone. While “Use my own keys” is enabled, generation will be unavailable until you enter new keys.</div>
  </EditorDialog>;
}
