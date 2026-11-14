import React, { useRef, useState } from "react";
import { HiOutlineScissors, HiOutlineArrowRight } from "react-icons/hi2";
import { EditorDialog, editorButton, editorSecondaryButton } from "./ui/EditorDialog";
import { VideoPreview } from "./VideoPreview";
import { CutTimeline, cutClock } from "./CutTimeline";
import { getVideoPreview, updateVideoCuts, updateSceneCuts } from "../api/apiService";
import { splitSections, removeSection, segmentAt } from "../utils/sections";
import { sectionsDuration } from "../utils/cuts";

export function VideoCuts(props) {
  return <TimelineCuts {...props} fullVideo />;
}

export function SceneCuts(props) {
  return <TimelineCuts {...props} />;
}

function TimelineCuts({ scene, video, index, disabled, onSaved, fullVideo = false }) {
  const sourceDuration = scene?.timing?.source_duration ?? scene?.timing?.duration ?? 0;
  const saved = (fullVideo ? video.cuts : scene?.cuts) || {};
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
  const apply = (next, selection = 0) => {
    if (!next || busy) return;
    setHistory(current => [...current, { sections, selected }]);
    setFuture([]);
    setSections(next);
    setSelected(selection);
  };
  const split = () => {
    const position = controls.current?.position ?? 0;
    apply(splitSections(sections, position), segmentAt(sections, position).index + 1);
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
    else if (!command && (event.key === "Delete" || event.key === "Backspace")) { event.preventDefault(); apply(removeSection(sections, selected)); }
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
      const payload = { source_duration: editDuration, sections, previous: session.previous };
      const result = fullVideo ? await updateVideoCuts(video.id, { ...payload, source_key: session.sourceKey }) : await updateSceneCuts(scene.id, payload);
      if (!result.ok) { setError(result.message || "Could not save cuts. Your changes are still here."); return; }
      setOpen(false); onSaved?.(true);
    } catch { setError("Could not save cuts. Your changes are still here; please retry."); }
    finally { setBusy(false); }
  };
  return <>
    <button type="button" disabled={disabled || busy || (!fullVideo && (!Number.isFinite(sourceDuration) || sourceDuration < 0.05))} onClick={async () => {
      setError("");
      let nextSession = { sourceDuration, previous: saved };
      let nextSections = initial;
      if (fullVideo) {
        setBusy(true);
        try {
          const response = await getVideoPreview(video.id);
          const manifest = response.data;
          if (!response.ok || !(manifest?.cut_source?.duration >= 0.05)) throw new Error(response.message || "Could not load the video timeline. Please retry.");
          const source = manifest.cut_source;
          nextSession = { sourceDuration: source.duration, sourceKey: source.key, previous: saved, manifest };
          nextSections = saved.source_key === source.key ? saved.sections : [{ start: 0, end: source.duration }];
        } catch (error) { setError(error.message || "Could not load the video timeline. Please retry."); return; }
        finally { setBusy(false); }
      }
      setSession(nextSession); setSections(nextSections); setHistory([]); setFuture([]); setSelected(0); setOpen(true);
    }} className="inline-flex min-h-11 items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 disabled:opacity-40 dark:text-blue-300 dark:hover:bg-white/5"><HiOutlineScissors aria-hidden="true" className="h-4 w-4" />{busy && !open ? "Loading timeline…" : fullVideo ? "Cut video" : "Cut scene"}</button>
    {!open && error && <p role="alert" className="text-sm text-red-600">{error}</p>}
    {open && <EditorDialog open onClose={() => setOpen(false)} busy={busy} title={fullVideo ? "Cut video" : `Cut scene ${index + 1}`} description={fullVideo ? "Cut across scenes, intro and outro. Scene edits stay intact." : "Shape the pace. Picture, sound, and captions stay together."} icon={HiOutlineScissors} maxWidth="max-w-5xl" panelClassName="cut-studio" footer={<div className="flex w-full flex-wrap items-center justify-between gap-3">
      <div className="cut-duration-summary"><span className="cut-original-duration">{cutClock(editDuration)}</span><HiOutlineArrowRight aria-hidden="true" /><strong>{cutClock(duration)}</strong><span className="cut-time-saved" role="status">{removed > 0.005 ? `${removed.toFixed(2)}s removed` : `${sections.length} ${sections.length === 1 ? "section" : "sections"}`}</span></div>
      <div className="flex items-center gap-2"><button type="button" disabled={busy} onClick={() => setOpen(false)} className={editorSecondaryButton}>Cancel</button><button type="button" disabled={busy || disabled} onClick={save} className={editorButton}>{busy ? "Saving…" : "Save cuts"}</button></div>
    </div>}>
      {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">{error}</p>}
      {fullVideo && session?.manifest?.cuts_stale && <p role="status" className="mb-3 text-sm text-amber-600">The timeline changed since the last full-video cut. Review new cuts before saving. Your scene cuts are preserved.</p>}
      <div onKeyDown={keyboard}>
        <VideoPreview disabled={busy} video={video} selectedSceneId={scene?.id} sceneOnly={!fullVideo} sourceManifest={session?.manifest} compact cutSections={sections} renderCutControls={state => {
          controls.current = state;
          return <CutTimeline scene={scene} fullVideo={fullVideo} sourceScenes={session?.manifest?.segments} sourceSections={session?.manifest?.cut_source.sections} sections={sections} sourceDuration={editDuration} position={state.position} selected={selected} onSelect={setSelected} onSeek={state.onSeek} onSplit={split} onRemove={() => apply(removeSection(sections, selected))} onUndo={undo} onRedo={redo} onReset={() => apply([{ start: 0, end: editDuration }])} canSplit={!!splitSections(sections, state.position)} canUndo={!!history.length} canRedo={!!future.length} disabled={busy || !state.ready} />;
        }} />
        <p className="cut-keyboard-help mt-3 text-center text-[11px]">Drag to scrub <span>·</span> <kbd>S</kbd> Split <span>·</span> <kbd>Delete</kbd> Remove <span>·</span> <kbd>←</kbd><kbd>→</kbd> Frame by frame <span>·</span> <kbd>Space</kbd> Play / pause</p>
      </div>
    </EditorDialog>}
  </>;
}
