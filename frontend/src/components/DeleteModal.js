import React, { useEffect, useState } from "react";
import { toast } from "react-toastify";
import { EditorDialog } from "./ui/EditorDialog";

export function DeleteModal({ showModal, setShowModal, id, setItems, deleteFunction, name, mode = "normal", recoveryHint }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { if (showModal) setError(""); }, [showModal, id]);
  const remove = async () => {
    if (busy) return;
    setBusy(true); setError("");
    try {
      const response = await deleteFunction(id);
      if (!response.ok) { setError(response.message || `Could not delete this ${name}. Please try again.`); return; }
      toast.success(`${name} deleted successfully`);
      if (mode === "normal") setItems(items => items.filter(item => item.id !== id));
      else setItems(true);
      setShowModal(false);
    } catch (reason) { setError(reason.message || "Could not delete this item. Please try again."); }
    finally { setBusy(false); }
  };
  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title={`Delete ${name}?`} description={`Are you sure you want to delete this ${name}?`} busy={busy} maxWidth="max-w-md" footer={<div className="flex flex-wrap justify-end gap-2">
    <button type="button" disabled={busy} onClick={() => setShowModal(false)} className="rounded-xl border border-gray-200 px-4 py-3 text-sm font-medium text-gray-600 disabled:opacity-40 dark:border-gray-600 dark:text-gray-300">Cancel</button>
    <button type="button" disabled={busy} onClick={remove} className="rounded-xl bg-red-600 px-4 py-3 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-40">{busy ? "Deleting…" : "Delete"}</button>
  </div>}>
    {recoveryHint && <p className="text-sm leading-relaxed text-gray-500 dark:text-gray-400">{recoveryHint}</p>}
    {error && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-300">{error}</p>}
  </EditorDialog>;
}
