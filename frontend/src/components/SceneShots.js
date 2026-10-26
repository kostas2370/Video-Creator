import { lazy, useState } from "react";
import { DeferredDialog } from "./ui/DeferredDialog";
import { EditorDialog, editorButton, editorInput } from "./ui/EditorDialog";
import { API_HOST } from "../endpoints";
import { updateSceneShots } from "../api/apiService";
import { MOTION_OPTIONS } from "../utils/motion";
import { isVideo } from "../utils/media";
import { moveShotBoundary, shotDurations } from "../utils/shots";

const EditSceneImageModal = lazy(() => import("./EditSceneImageModal").then(module => ({ default: module.EditSceneImageModal })));
const source = file => /^https?:\/\//i.test(file || "") ? file : API_HOST + file;
const button = "rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium text-gray-700 disabled:opacity-40 dark:border-gray-600 dark:text-gray-200";

export function SceneShots({ scene, disabled, onSaved, videoFormat }) {
  const shots = scene.shots || [];
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  return <div className="mt-4">
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" disabled={disabled || shots.length >= 20} onClick={() => setEditing({ new_shot: true })} className={button}>+ Add shot</button>
      {shots.length > 1 && <button type="button" disabled={disabled} onClick={() => setOpen(true)} className={button}>Manage {shots.length} shots</button>}
    </div>
    {shots.length > 1 ? <div className="mt-3 flex gap-2 overflow-x-auto pb-1">{shots.map((shot, index) => <button key={shot.id} type="button" disabled={disabled} onClick={() => setEditing(shot)} aria-label={`Edit shot ${index + 1}`} className="w-24 shrink-0 overflow-hidden rounded-lg border border-gray-200 text-left dark:border-gray-600"><ShotThumbnail shot={shot} /><span className="block px-2 py-1 text-xs">Shot {index + 1}</span></button>)}</div> : <p className="mt-2 text-xs text-gray-500">Add another visual while keeping the same narration.</p>}
    {open && <ShotEditor scene={scene} disabled={disabled} onClose={() => setOpen(false)} onSaved={onSaved} />}
    <DeferredDialog open={!!editing} onClose={() => setEditing(null)}>{editing && <EditSceneImageModal showModal setShowModal={() => setEditing(null)} setUpdate={onSaved} scene_info={{ scene_id: scene.id, video_id: scene.video, video_format: videoFormat, scene_image_id: editing.id, image: editing.file ? source(editing.file) : "", prompt: editing.prompt, with_audio: editing.with_audio, new_shot: editing.new_shot }} />}</DeferredDialog>
  </div>;
}

function ShotThumbnail({ shot }) {
  return <div className="aspect-video overflow-hidden bg-gray-100 dark:bg-gray-900">{shot.file ? isVideo(shot.file) ? <video src={source(shot.file)} muted preload="metadata" className="h-full w-full object-cover" /> : <img src={source(shot.file)} alt="" className="h-full w-full object-cover" /> : <span className="flex h-full items-center justify-center text-xs text-gray-400">No visual</span>}</div>;
}

function ShotEditor({ scene, disabled, onClose, onSaved }) {
  const [shots, setShots] = useState(() => scene.shots.map(shot => ({ ...shot })));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(null);
  const duration = scene.timing?.base_duration || 1;
  const durations = shotDurations(shots, duration);
  const patch = (id, changes) => setShots(rows => rows.map(row => row.id === id ? { ...row, ...changes } : row));
  const move = (from, to) => setShots(rows => { const next = [...rows]; const [shot] = next.splice(from, 1); next.splice(to, 0, shot); return next; });
  const save = async () => {
    setBusy(true); setError("");
    try {
      const response = await updateSceneShots(scene.id, shots.map(({ id, timing_weight, trim_start, motion_style, motion_intensity, with_audio }) => ({ id, timing_weight, trim_start, motion_style, motion_intensity, with_audio })), scene.shots.map(shot => shot.id));
      if (response.ok) { onSaved(true); onClose(); }
      else setError(response.message || "Could not save shots. Please try again.");
    } catch { setError("Could not save shots. Please try again."); }
    finally { setBusy(false); }
  };
  const locked = disabled || busy;
  return <EditorDialog open onClose={onClose} busy={busy} title="Scene shots" description="Drag shots or use the arrow buttons to reorder. Adjust cut points below; narration and captions continue across shots.">
    {error && <p role="alert" className="mb-3 text-sm text-red-600 dark:text-red-300">{error}</p>}
    <div className="space-y-3">{shots.map((shot, index) => {
      const start = durations.slice(0, index).reduce((a, b) => a + b, 0);
      const end = start + durations[index];
      return <div key={shot.id} draggable={!locked} onDragStart={() => setDragging(index)} onDragEnd={() => setDragging(null)} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); if (!locked && dragging !== null) move(dragging, index); setDragging(null); }} className="rounded-xl border border-gray-200 p-3 dark:border-gray-700">
        <div className="flex flex-wrap items-center gap-3"><div className="w-24 shrink-0 overflow-hidden rounded-lg"><ShotThumbnail shot={shot} /></div><div className="flex-1"><p className="text-sm font-semibold">Shot {index + 1}</p><p className="text-xs text-gray-500">{start.toFixed(2)}–{end.toFixed(2)}s · {durations[index].toFixed(2)}s</p></div><button type="button" aria-label={`Move shot ${index + 1} earlier`} disabled={locked || index === 0} onClick={() => move(index, index - 1)} className={button}>←</button><button type="button" aria-label={`Move shot ${index + 1} later`} disabled={locked || index === shots.length - 1} onClick={() => move(index, index + 1)} className={button}>→</button><button type="button" disabled={locked || shots.length === 1} onClick={() => setShots(rows => rows.filter(row => row.id !== shot.id))} className={button}>Remove</button></div>
        <div className="mt-3 flex flex-wrap items-center gap-3">{isVideo(shot.file) ? <><label className="text-xs">Clip starts at (seconds)<input aria-label={`Shot ${index + 1} clip start`} type="number" min="0" max="900" step="0.1" disabled={locked} value={shot.trim_start} onChange={event => patch(shot.id, { trim_start: Number(event.target.value) })} className={`${editorInput} mt-1 w-28`} /></label><label className="flex items-center gap-2 text-xs"><input type="checkbox" disabled={locked} checked={shot.with_audio} onChange={event => patch(shot.id, { with_audio: event.target.checked })} />Keep clip audio</label></> : <label className="text-xs">Image motion<select aria-label={`Shot ${index + 1} motion`} disabled={locked} value={shot.motion_style || ""} onChange={event => patch(shot.id, { motion_style: event.target.value || null })} className={`${editorInput} mt-1`}><option value="">Use scene setting</option>{MOTION_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>}</div>
        {index < shots.length - 1 && <label className="mt-3 block text-xs text-gray-500">Cut after shot {index + 1}: {end.toFixed(2)}s<input aria-label={`Cut after shot ${index + 1}`} type="range" disabled={locked} min={start + Math.min(0.05, durations[index] / 4)} max={end + durations[index + 1] - Math.min(0.05, durations[index + 1] / 4)} step="0.01" value={end} onChange={event => setShots(moveShotBoundary(shots, index, Number(event.target.value), duration))} className="mt-2 block w-full accent-blue-600" /></label>}
      </div>;
    })}</div>
    <p className="mt-3 text-xs text-gray-500">Shot lengths scale with scene duration. The final shot includes any ending pause. Removed media stays in your library.</p>
    <footer className="mt-5 flex justify-end gap-3"><button type="button" disabled={busy} onClick={onClose} className={button}>Cancel</button><button type="button" disabled={locked} onClick={save} className={editorButton}>{busy ? "Saving…" : "Save shots"}</button></footer>
  </EditorDialog>;
}
