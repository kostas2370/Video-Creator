import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { deleteDraftVideo } from "../api/apiService";
import { DeleteModal } from "./DeleteModal";

export function DeleteDraftProject({ id, disabled = false, onDeleted }) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const remove = async projectId => {
    const result = await deleteDraftVideo(projectId);
    return result.status === 404 ? { ...result, ok: true } : result;
  };
  return <>
    <button type="button" disabled={disabled} onClick={() => setOpen(true)} className="rounded-lg px-2 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-40 dark:text-red-300 dark:hover:bg-red-950/30">Delete draft project</button>
    <DeleteModal showModal={open} setShowModal={setOpen} id={id} name="draft project" mode="image" deleteFunction={remove} setItems={() => { if (onDeleted) onDeleted(); else navigate("/videos/"); }} recoveryHint="This permanently removes the saved draft project. Reusable media in your library is kept." />
  </>;
}
