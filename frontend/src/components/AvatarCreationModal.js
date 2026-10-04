import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { createAvatar, getVoices } from "../api/apiService";
import { toast } from "react-toastify";
import { EditorDialog, editorInput, editorButton } from "./ui/EditorDialog";

export const AvatarCreationModal = ({ showModal, setShowModal, setAvatars, onCreated }) => {
  const [voices, setVoices] = useState([]);
  const [voice, setVoice] = useState("");
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState("");
  const [name, setName] = useState("");
  const [gender, setGender] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadingVoices, setLoadingVoices] = useState(false);
  useEffect(() => {
    if (!showModal) return;
    let current = true;
    setName(""); setVoice(""); setGender(""); setImage(null); setLoadingVoices(true);
    getVoices().then(({ data: response }) => { if (current) { setVoices(Array.isArray(response) ? response : []); setLoadingVoices(false); } });
    return () => { current = false; };
  }, [showModal]);
  useEffect(() => {
    if (!image) { setPreview(""); return; }
    const url = URL.createObjectURL(image); setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [image]);
  const selected = voices.find(item => String(item.id) === voice);
  const onSubmit = async event => {
    event.preventDefault(); setBusy(true);
    try {
      const data = new FormData(); data.append("name", name); data.append("file", image); data.append("voice", voice); data.append("gender", gender);
      const { data: response } = await createAvatar(data);
      if (response) { setAvatars(items => [...items, response]); toast.success("Avatar created successfully"); setShowModal(false); onCreated?.(); }
    } catch { toast.error("Could not create your avatar. Please try again."); }
    finally { setBusy(false); }
  };
  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title="Create avatar" description="Pair a portrait with a voice to bring your presenter to life." busy={busy}>
    <form onSubmit={onSubmit}>
      <div className="grid gap-6 sm:grid-cols-2"><div><label htmlFor="avatar-image" className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Portrait image</label><div className="mb-3 flex aspect-square items-center justify-center overflow-hidden rounded-xl border border-dashed border-gray-200 bg-gray-50 dark:border-gray-600 dark:bg-gray-900">{preview ? <img src={preview} alt="New avatar preview" className="h-full w-full object-cover" /> : <p className="px-6 text-center text-sm text-gray-400">Choose a clear, front-facing portrait</p>}</div><input key={String(showModal)} id="avatar-image" type="file" accept="image/*" required disabled={busy} onChange={e => setImage(e.target.files[0] || null)} className={editorInput} /></div>
        <div className="space-y-4"><div><label htmlFor="avatar-name" className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Avatar name</label><input id="avatar-name" required maxLength={100} placeholder="e.g. Studio presenter" value={name} disabled={busy} onChange={e => setName(e.target.value)} className={editorInput} /></div><div><label htmlFor="avatar-gender" className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Gender</label><select id="avatar-gender" required value={gender} disabled={busy} onChange={e => setGender(e.target.value)} className={editorInput}><option value="">Choose gender</option><option value="fem">Female</option><option value="mal">Male</option><option value="oth">Other</option></select></div><div><label htmlFor="avatar-voice" className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Voice</label><select id="avatar-voice" required value={voice} disabled={busy || loadingVoices || !voices.length} onChange={e => setVoice(e.target.value)} className={editorInput}><option value="">{loadingVoices ? "Loading voices…" : "Choose a voice"}</option>{voices.map(item => <option key={item.id} value={item.id}>{item.name} · {item.provider}</option>)}</select>{!loadingVoices && !voices.length && <p className="mt-2 text-xs text-gray-500">No voices available. <Link to="/api-keys/" className="text-blue-600 dark:text-blue-400">Check your provider settings</Link>.</p>}</div>{selected?.sample && <audio aria-label="Selected voice preview" key={selected.id} src={selected.sample} controls className="h-10 w-full" />}</div>
      </div><footer className="mt-6 flex justify-end gap-3"><button type="button" disabled={busy} onClick={() => setShowModal(false)} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 dark:text-gray-300">Cancel</button><button type="submit" disabled={busy || !image || !name.trim() || !gender || !voice} className={editorButton}>{busy ? "Creating…" : "Create avatar"}</button></footer>
    </form>
  </EditorDialog>;
};
