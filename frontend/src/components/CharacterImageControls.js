import { useEffect, useState } from "react";
import { createCharacterReference, getCharacterReference } from "../api/apiService";
import { API_HOST } from "../endpoints";
import { characterApproval, characterIsApproved } from "../utils/series";

export const characterImageUrl = url => url && (/^https?:\/\//i.test(url) ? url : `${API_HOST}${url}`);

export function CharacterImageControls({ character, visualStyle, onPatch }) {
  const [job, setJob] = useState(character.reference_job_id || null);
  const [candidate, setCandidate] = useState(null);
  const [busy, setBusy] = useState(!!character.reference_job_id);
  const [error, setError] = useState("");
  const [check, setCheck] = useState(0);
  useEffect(() => {
    if (!job) return;
    let active = true, timer;
    const started = Date.now();
    const poll = async () => {
      const response = await getCharacterReference(job);
      if (!active) return;
      if (!response.ok) { setError(response.message); setBusy(false); return; }
      if (response.data.status === "READY") { setCandidate(response.data); setJob(null); setBusy(false); return; }
      if (response.data.status === "FAILED") { setError(response.data.error); setJob(null); setBusy(false); onPatch({ reference_job_id: null }); return; }
      if (Date.now() - started > 10 * 60 * 1000) { setError("This image is taking longer than expected. Check its progress again before starting another request."); setBusy(false); return; }
      timer = setTimeout(poll, 3000);
    };
    poll();
    return () => { active = false; clearTimeout(timer); };
  }, [job, check]);
  const create = async file => {
    if (busy || job) return;
    setBusy(true); setError("");
    const choices = { id: character.id, name: character.name, appearance: character.appearance, wardrobe: character.wardrobe || "", visual_style: visualStyle };
    let payload = choices;
    if (file) {
      if (!/image\/(png|jpeg|webp)/.test(file.type) || file.size > 10 * 1024 * 1024) { setError("Choose a PNG, JPEG or WebP image smaller than 10 MB."); setBusy(false); return; }
      payload = new FormData(); Object.entries(choices).forEach(([key, value]) => payload.append(key, value)); payload.append("image", file);
    }
    const response = await createCharacterReference(payload);
    if (!response.ok) { setError(response.message); setBusy(false); return; }
    onPatch({ reference_job_id: response.data.id });
    if (response.data.status === "READY") { setCandidate(response.data); setBusy(false); }
    else setJob(response.data.id);
  };
  const ready = !!(character.name.trim() && character.appearance.trim() && visualStyle.trim());
  const approved = characterIsApproved(character, visualStyle);
  return <div className="space-y-3 rounded-xl bg-gray-50 p-4 dark:bg-gray-900/50">
    <p className="text-sm font-semibold">Character reference image</p>
    {character.reference_image && <><img src={characterImageUrl(character.reference_image)} alt={`${character.name || "Character"} approved reference`} className="max-h-56 rounded-lg object-contain" /><p role="status" className={`text-xs ${approved ? "text-green-700 dark:text-green-300" : "text-amber-700 dark:text-amber-300"}`}>{approved ? "Look approved for future episodes" : "Review this image after changing the character or visual style."}</p>{!approved && <button type="button" onClick={() => onPatch({ reference_approval: characterApproval(character, visualStyle) })} className="text-sm font-semibold text-indigo-600 dark:text-indigo-300">Approve current look</button>}</>}
    {candidate && <div className="space-y-3 border-t border-gray-200 pt-4 dark:border-gray-700"><p className="text-sm font-semibold">Review new character image</p><img src={characterImageUrl(candidate.image)} alt={`Proposed reference for ${character.name}`} className="max-h-64 rounded-lg object-contain" /><div className="flex gap-4"><button type="button" onClick={() => { const next = { ...character, reference_id: candidate.id }; onPatch({ reference_id: candidate.id, reference_job_id: null, reference_image: candidate.image, reference_approval: characterApproval(next, visualStyle) }); setCandidate(null); }} className="text-sm font-semibold text-indigo-600 dark:text-indigo-300">Use this look</button><button type="button" onClick={() => { onPatch({ reference_job_id: null }); setCandidate(null); }} className="text-sm text-gray-500">Discard new image</button></div></div>}
    <div className="flex flex-wrap items-center gap-4"><button type="button" disabled={busy || !!job || !ready} onClick={() => create()} className="rounded-lg border border-indigo-300 px-3 py-2 text-sm font-semibold text-indigo-600 disabled:opacity-50 dark:text-indigo-300">{busy ? "Preparing image…" : character.reference_id ? "Generate another look with AI" : "Generate character image with AI"}</button><label className="text-sm font-semibold">Upload reference<input aria-label={`Upload reference for ${character.name || "character"}`} type="file" accept="image/png,image/jpeg,image/webp" disabled={busy || !!job || !ready} className="mt-2 block max-w-full text-xs" onChange={event => { const file = event.target.files?.[0]; if (file) create(file); event.target.value = ""; }} /></label></div>
    {!ready && <p className="text-xs text-gray-500">Add a name, appearance and signature visual style first.</p>}
    <p className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">Generate with the configured OpenAI image model or upload your own image. AI generation uses provider credits. Your saved look stays in place until you accept a replacement.</p>
    {error && <p role="alert" className="text-sm text-red-600 dark:text-red-300">{error}</p>}
    {job && !busy && <button type="button" onClick={() => { setError(""); setBusy(true); setCheck(value => value + 1); }} className="text-sm font-semibold text-indigo-600 dark:text-indigo-300">Check image progress</button>}
  </div>;
}
