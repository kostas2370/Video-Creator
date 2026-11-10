import React, { useRef, useState } from "react";
import { HiOutlineScissors, HiOutlineArrowRight } from "react-icons/hi2";
import { EditorDialog, editorButton, editorSecondaryButton } from "./ui/EditorDialog";
import { VideoPreview } from "./VideoPreview";
import { CutTimeline, cutClock } from "./CutTimeline";
import { updateSceneCuts } from "../api/apiService";
import { clipSegments, splitClip, removeClipSection, segmentAt } from "../utils/clips";
import { sectionsDuration } from "../utils/cuts";

export function SceneCuts({ scene, video, index, disabled, onSaved }) {
  const sourceDuration = scene.timing?.source_duration ?? scene.timing?.duration;
  const saved = scene.cuts || {};
  const initial = saved.sections && Math.abs(saved.source_duration - sourceDuration) <= 0.001 ? saved.sections : [{ start: 0, end: sourceDuration }];
  const [sections, setSections] = useState(initial);
  const [history, setHistory] = useState([]);
  const [future, setFuture] = useState([]);
  const [selected, setSelected] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [session, setSession] = useState(null);
  const controls = useRef(null);
  const editDuration = session?.sourceDuration ?? sourceDuration;
  const duration = sectionsDuration(sections);
  const removed = Math.max(0, editDuration - duration);
  const draft = { start: 0, end: editDuration, segments: sections, words: [] };
  const apply = (next, selection = 0) => {
    if (!next || busy) return;
    setHistory(current => [...current, { sections, selected }]);
    setFuture([]);
    setSections(clipSegments(next));
    setSelected(selection);
  };
  const split = () => {
    const position = controls.current?.position ?? 0;
    apply(splitClip(draft, position), segmentAt(sections, position).index + 1);
  };
  const undo = () => {
    if (!history.length || busy) return;
    const previous = history[history.length - 1];
    setFuture(current => [...current, { sections, selected }]);
    setHistory(current => current.slice(0, -1));
    setSections(previous.sections);
    setSelected(previous.selected);
  };
  const redo = () => {
    if (!future.length || busy) return;
    const next = future[future.length - 1];
    setHistory(current => [...current, { sections, selected }]);
    setFuture(current => current.slice(0, -1));
    setSections(next.sections);
    setSelected(next.selected);
  };
  const keyboard = event => {
    const target = event.target;
    if (event.defaultPrevented || busy || disabled || !controls.current?.ready || target.isContentEditable || /^(TEXTAREA|SELECT)$/.test(target.tagName) || (target.tagName === "INPUT" && target.type !== "range")) return;
    const command = event.metaKey || event.ctrlKey;
    if (command && event.key.toLowerCase() === "z") { event.preventDefault(); event.shiftKey ? redo() : undo(); }
    else if (!command && !event.altKey && event.key.toLowerCase() === "s") { event.preventDefault(); split(); }
    else if (!command && (event.key === "Delete" || event.key === "Backspace")) { event.preventDefault(); apply(removeClipSection(draft, selected)); }
    else if (target.getAttribute("role") === "slider") {
      if (event.key === " ") { event.preventDefault(); controls.current.onTogglePlayback(); }
      else if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
        event.preventDefault();
        const step = (event.shiftKey ? 10 : 1) / (video.settings?.export_fps || 24);
        const next = event.key === "Home" ? 0 : event.key === "End" ? duration : controls.current.position + (event.key === "ArrowLeft" ? -step : step);
        controls.current.onSeek(Math.max(0, Math.min(duration, next)));
      }
    }
  };
  const save = async () => {
    setBusy(true); setError("");
    try {
      const result = await updateSceneCuts(scene.id, { source_duration: editDuration, sections, previous: session.previous });
      if (!result.ok) { setError(result.message || "Could not save cuts. Your changes are still here."); return; }
      setOpen(false); onSaved?.(true);
    } catch { setError("Could not save cuts. Your changes are still here; please retry."); }
    finally { setBusy(false); }
  };
  return <>
    <button type="button" disabled={disabled || !Number.isFinite(sourceDuration) || sourceDuration < 0.05} onClick={() => {
      setSession({ sourceDuration, previous: saved }); setSections(initial); setHistory([]); setFuture([]); setSelected(0); setError(""); setOpen(true);
    }} className="inline-flex min-h-11 items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 disabled:opacity-40 dark:text-blue-300 dark:hover:bg-white/5"><HiOutlineScissors aria-hidden="true" className="h-4 w-4" />Cut scene</button>
    {open && <EditorDialog open onClose={() => setOpen(false)} busy={busy} title={`Cut scene ${index + 1}`} description="Shape the pace. Picture, sound, and captions stay together." icon={HiOutlineScissors} maxWidth="max-w-5xl" panelClassName="cut-studio" footer={<div className="flex w-full flex-wrap items-center justify-between gap-3">
      <div className="cut-duration-summary"><span className="cut-original-duration">{cutClock(editDuration)}</span><HiOutlineArrowRight aria-hidden="true" /><strong>{cutClock(duration)}</strong><span className="cut-time-saved" role="status">{removed > 0.005 ? `${removed.toFixed(2)}s removed` : `${sections.length} ${sections.length === 1 ? "section" : "sections"}`}</span></div>
      <div className="flex items-center gap-2"><button type="button" disabled={busy} onClick={() => setOpen(false)} className={editorSecondaryButton}>Cancel</button><button type="button" disabled={busy || disabled} onClick={save} className={editorButton}>{busy ? "Saving…" : "Save cuts"}</button></div>
    </div>}>
      {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">{error}</p>}
      <div onKeyDown={keyboard}>
        <VideoPreview disabled={busy} video={video} selectedSceneId={scene.id} sceneOnly compact cutSections={sections} renderCutControls={state => {
          controls.current = state;
          return <CutTimeline scene={scene} sections={sections} sourceDuration={editDuration} position={state.position} selected={selected} onSelect={setSelected} onSeek={state.onSeek} onSplit={split} onRemove={() => apply(removeClipSection(draft, selected))} onUndo={undo} onRedo={redo} onReset={() => apply({ ...draft, segments: [{ start: 0, end: editDuration }] })} canSplit={!!splitClip(draft, state.position)} canUndo={!!history.length} canRedo={!!future.length} disabled={busy || !state.ready} />;
        }} />
        <p className="cut-keyboard-help mt-3 text-center text-[11px]">Drag to scrub <span>·</span> <kbd>S</kbd> Split <span>·</span> <kbd>Delete</kbd> Remove <span>·</span> <kbd>←</kbd><kbd>→</kbd> Frame by frame <span>·</span> <kbd>Space</kbd> Play / pause</p>
      </div>
    </EditorDialog>}
  </>;
}
