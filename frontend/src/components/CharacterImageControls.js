import { useEffect, useState } from "react";
import { createCharacterReference, getCharacterReference } from "../api/apiService";
import { mediaUrl } from "../utils/media";
import { characterIsApproved } from "../utils/series";

const inProgress = status => ["QUEUED", "GENERATING"].includes(status);

export function CharacterImageControls({ character, visualStyle, onPatch }) {
  const [job, setJob] = useState(inProgress(character.status));
  const [candidate, setCandidate] = useState(character.pending_image || null);
  const [busy, setBusy] = useState(inProgress(character.status));
  const [error, setError] = useState("");
  const [check, setCheck] = useState(0);

  const receiveImage = data => {
    const image = data.pending_image || data.image;
    setCandidate(image);
    setJob(false);
    setBusy(false);
    onPatch({ status: data.status, pending_image: image, error: "" });
  };

  useEffect(() => {
    if (!job) return;
    let active = true, timer;
    const started = Date.now();
    const poll = async () => {
      const response = await getCharacterReference(character.id);
      if (!active) return;
      if (!response.ok) { setError(response.message); setBusy(false); return; }
      if (response.data.status === "READY") { receiveImage(response.data); return; }
      if (response.data.status === "FAILED") {
        setError(response.data.error); setJob(false); setBusy(false);
        onPatch({ status: "FAILED", error: response.data.error });
        return;
      }
      if (Date.now() - started > 10 * 60 * 1000) {
        setError("This image is taking longer than expected. Check its progress again before starting another request.");
        setBusy(false); return;
      }
      timer = setTimeout(poll, 3000);
    };
    poll();
    return () => { active = false; clearTimeout(timer); };
  }, [job, check, character.id]);

  const create = async file => {
    if (busy || job) return;
    setBusy(true); setError("");
    const choices = { id: character.id, name: character.name, appearance: character.appearance, wardrobe: character.wardrobe || "", visual_style: visualStyle };
    let payload = choices;
    if (file) {
      if (!/image\/(png|jpeg|webp)/.test(file.type) || file.size > 10 * 1024 * 1024) {
        setError("Choose a PNG, JPEG or WebP image smaller than 10 MB."); setBusy(false); return;
      }
      payload = new FormData();
      Object.entries(choices).forEach(([key, value]) => payload.append(key, value));
      payload.append("image", file);
    }
    const response = await createCharacterReference(payload);
    if (!response.ok) { setError(response.message); setBusy(false); return; }
    onPatch({ status: response.data.status, error: "" });
    if (response.data.status === "READY") receiveImage(response.data);
    else setJob(true);
  };
  const approve = image => {
    onPatch({ image, pending_image: null, image_approved: true, visual_style: visualStyle, status: "READY" });
    setCandidate(null);
  };
  const ready = !!(character.name.trim() && character.appearance.trim() && visualStyle.trim());
  const approved = characterIsApproved(character, visualStyle);

  return <div className="space-y-3 rounded-xl bg-gray-50 p-4 dark:bg-gray-900/50">
    <p className="text-sm font-semibold">Character reference image</p>
    {character.image && <>
      <img src={mediaUrl(character.image)} alt={`${character.name || "Character"} approved reference`} className="max-h-56 rounded-lg object-contain" />
      <p role="status" className={`text-xs ${approved ? "text-green-700 dark:text-green-300" : "text-amber-700 dark:text-amber-300"}`}>{approved ? "Look approved for future episodes" : "Review this image after changing the character or visual style."}</p>
      {!approved && <button type="button" onClick={() => approve(character.image)} className="text-sm font-semibold text-indigo-600 dark:text-indigo-300">Approve current look</button>}
    </>}
    {candidate && <div className="space-y-3 border-t border-gray-200 pt-4 dark:border-gray-700">
      <p className="text-sm font-semibold">Review new character image</p>
      <img src={mediaUrl(candidate)} alt={`Proposed reference for ${character.name}`} className="max-h-64 rounded-lg object-contain" />
      <div className="flex gap-4">
        <button type="button" onClick={() => approve(candidate)} className="text-sm font-semibold text-indigo-600 dark:text-indigo-300">Use this look</button>
        <button type="button" onClick={() => setCandidate(null)} className="text-sm text-gray-500">Review later</button>
      </div>
    </div>}
    <div className="flex flex-wrap items-center gap-4">
      <button type="button" disabled={busy || job || !ready} onClick={() => create()} className="rounded-lg border border-indigo-300 px-3 py-2 text-sm font-semibold text-indigo-600 disabled:opacity-50 dark:text-indigo-300">{busy ? "Preparing image…" : character.image ? "Generate another look with AI" : "Generate character image with AI"}</button>
      <label className="text-sm font-semibold">Upload reference<input aria-label={`Upload reference for ${character.name || "character"}`} type="file" accept="image/png,image/jpeg,image/webp" disabled={busy || job || !ready} className="mt-2 block max-w-full text-xs" onChange={event => { const file = event.target.files?.[0]; if (file) create(file); event.target.value = ""; }} /></label>
    </div>
    {!ready && <p className="text-xs text-gray-500">Add a name, appearance and signature visual style first.</p>}
    <p className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">Generate with the configured OpenAI image model or upload your own image. AI generation uses provider credits. Your saved look stays in place until you accept a replacement.</p>
    {error && <p role="alert" className="text-sm text-red-600 dark:text-red-300">{error}</p>}
    {job && !busy && <button type="button" onClick={() => { setError(""); setBusy(true); setCheck(value => value + 1); }} className="text-sm font-semibold text-indigo-600 dark:text-indigo-300">Check image progress</button>}
  </div>;
}
