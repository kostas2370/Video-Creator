import { useState, useEffect } from "react";
import { toast } from "react-toastify";
import { EditorDialog, editorInput, editorButton } from "./ui/EditorDialog";

export function AssetCreationModal({ showModal, setShowModal, nameh1, ApiCall, setItems, onCreated }) {
  const [name, setName] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (showModal) { setName(""); setFile(null); } }, [showModal]);
  useEffect(() => {
    if (!file) { setPreview(""); return; }
    const url = URL.createObjectURL(file); setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const onSubmit = async event => {
    event.preventDefault(); setBusy(true);
    try {
      const data = new FormData(); data.append("name", name); data.append("file", file);
      const { data: response } = await ApiCall(data);
      if (response) { toast.success(`${nameh1} added successfully`); setItems(items => [...items, response]); setShowModal(false); onCreated?.(); }
    } catch { toast.error(`Could not upload your ${nameh1.toLowerCase()}. Please try again.`); }
    finally { setBusy(false); }
  };
  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title={`Add ${nameh1.toLowerCase()}`} description="Upload a reusable video clip for your opening or closing sequence." busy={busy}>
    <form onSubmit={onSubmit} className="space-y-5"><div><label htmlFor={`${nameh1}-name`} className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Clip name</label><input id={`${nameh1}-name`} required value={name} disabled={busy} onChange={e => setName(e.target.value)} placeholder="e.g. Studio opening" className={editorInput} /></div><div><label htmlFor={`${nameh1}-file`} className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Video file</label><input key={String(showModal)} id={`${nameh1}-file`} type="file" accept="video/*" required disabled={busy} onChange={e => setFile(e.target.files[0] || null)} className={editorInput} /></div>{preview && <video aria-label="New clip preview" src={preview} controls className="max-h-64 w-full rounded-xl bg-gray-900" />}<footer className="flex justify-end gap-3"><button type="button" disabled={busy} onClick={() => setShowModal(false)} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 dark:text-gray-300">Cancel</button><button type="submit" disabled={busy || !name.trim() || !file} className={editorButton}>{busy ? "Uploading…" : `Add ${nameh1.toLowerCase()}`}</button></footer></form>
  </EditorDialog>;
}
