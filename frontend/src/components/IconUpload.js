import { useEffect, useRef, useState } from "react";
import { uploadIcon } from "../api/apiService";
import { editorInput, editorButton } from "./ui/EditorDialog";

export function IconUpload({ index, onUploaded }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  const upload = async () => {
    if (busy || !file || !name.trim()) return;
    setBusy(true); setError("");
    const data = new FormData();
    data.append("name", name.trim()); data.append("description", description.trim()); data.append("file", file);
    try {
      const response = await uploadIcon(data);
      if (!active.current) return;
      if (response.ok) onUploaded(response.data);
      else setError(response.message || "Could not upload your icon. Try again.");
    } catch { if (active.current) setError("Could not upload your icon. Try again."); }
    finally { if (active.current) setBusy(false); }
  };
  return <details className="rounded-lg border border-gray-200 p-3 dark:border-gray-600">
    <summary className="cursor-pointer text-sm font-medium">Upload your own icon</summary>
    <fieldset disabled={busy} className="mt-3 space-y-3" onKeyDown={event => { if (event.key === "Enter" && event.target.type === "text") { event.preventDefault(); upload(); } }}>
      <p className="text-xs text-gray-500 dark:text-gray-400">PNG, JPEG or WebP · Up to 10 MB and 4 million pixels. Transparent PNG works best. Saved to your icon library for reuse.</p>
      <label className="block text-sm">Icon name for item {index + 1}<input className={editorInput} maxLength={160} value={name} onChange={event => setName(event.target.value)} /></label>
      <label className="block text-sm">Description for item {index + 1}<input className={editorInput} maxLength={500} placeholder="What the icon represents (optional)" value={description} onChange={event => setDescription(event.target.value)} /></label>
      <label className="block text-sm">Icon file for item {index + 1}<input className={editorInput} type="file" accept="image/png,image/jpeg,image/webp" onChange={event => {
        const selected = event.target.files?.[0];
        setError("");
        if (selected?.size > 10 * 1024 * 1024) { setFile(null); setError("Use an icon smaller than 10 MB."); event.target.value = ""; }
        else setFile(selected || null);
      }} /></label>
      <button type="button" disabled={busy || !file || !name.trim()} onClick={upload} className={editorButton}>{busy ? "Uploading…" : "Upload and use icon"}</button>
    </fieldset>
    {error && <p role="alert" className="mt-2 text-sm text-red-600">{error}</p>}
  </details>;
}
