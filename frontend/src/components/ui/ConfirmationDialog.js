import { useEffect, useState } from "react";
import { HiOutlineTrash } from "react-icons/hi2";
import { EditorDialog, editorDangerButton, editorSecondaryButton } from "./EditorDialog";

export function ConfirmationDialog({ open, onClose, onConfirm, title, description, confirmLabel = "Delete", cancelLabel = "Cancel" }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { if (open) setError(""); }, [open]);
  const confirm = async () => {
    if (busy) return;
    setBusy(true); setError("");
    try {
      const response = await onConfirm();
      if (response?.ok === false) setError(response.message || "Could not complete this action. Please try again.");
      else onClose();
    } catch (reason) { setError(reason.message || "Could not complete this action. Please try again."); }
    finally { setBusy(false); }
  };
  return <EditorDialog open={open} onClose={onClose} title={title} description={description} icon={HiOutlineTrash} tone="danger" busy={busy} maxWidth="max-w-lg" footer={<div className="flex flex-wrap justify-end gap-2"><button type="button" disabled={busy} onClick={onClose} className={editorSecondaryButton}>{cancelLabel}</button><button type="button" disabled={busy} onClick={confirm} className={editorDangerButton}>{busy ? "Working…" : confirmLabel}</button></div>}>
    {error ? <p role="alert" className="text-sm text-red-600 dark:text-red-300">{error}</p> : null}
  </EditorDialog>;
}
