import { editorToolButton } from "./ui/editorStyles";
import { useEffect, useMemo, useRef, useState } from "react";
import { HiOutlineChatBubbleBottomCenterText } from "react-icons/hi2";
import { getSceneCaptions, updateSceneCaptions } from "../api/apiService";
import { API_HOST } from "../endpoints";
import { captionAt, captionGroups, validateCaptionWords } from "../utils/captions";
import { isVideo } from "../utils/media";
import { CaptionWordEditor } from "./CaptionWordEditor";
import { CaptionLayer } from "./CaptionLayer";
import { EditorDialog, editorButton } from "./ui/EditorDialog";

const mediaUrl = path => /^https?:\/\//i.test(path) ? path : `${API_HOST}${path}`;

export function SceneCaptions({ scene, index, disabled, onSaved, videoFormat }) {
  const [open, setOpen] = useState(false);
  const trigger = useRef(null);
  const close = () => { setOpen(false); requestAnimationFrame(() => trigger.current?.focus()); };
  return <>
    <button ref={trigger} type="button" disabled={disabled || scene.narration_status !== "available"} onClick={() => setOpen(true)} aria-label={`Edit captions for scene ${index + 1}`} aria-haspopup="dialog" aria-expanded={open} title={scene.narration_status !== "available" ? "Add narration or a voiceover to edit timed captions" : "Correct caption words and their timing"} className={editorToolButton}>
      <HiOutlineChatBubbleBottomCenterText aria-hidden="true" className="h-5 w-5" />Captions
    </button>
    {open && <SceneCaptionEditor scene={scene} index={index} disabled={disabled} onSaved={onSaved} onClose={close} videoFormat={videoFormat} />}
  </>;
}

export function SceneCaptionEditor({ scene, index, disabled, onSaved, onClose, videoFormat }) {
  const [data, setData] = useState(null);
  const [words, setWords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState("");
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const player = useRef(null);
  const saving = useRef(false);
  const groups = useMemo(() => captionGroups(words, data?.config || data?.style || "CLASSIC"), [words, data?.style, data?.config]);
  const cue = useMemo(() => captionAt(groups, time, data?.config || data?.style || "CLASSIC"), [groups, time, data?.style, data?.config]);
  const size = videoFormat === "PORTRAIT" ? [1080, 1920] : videoFormat === "SQUARE" ? [1080, 1080] : [1920, 1080];
  const locked = loading || busy || disabled;
  const close = () => { if (!saving.current && (!dirty || window.confirm("Discard unsaved caption changes?"))) onClose(); };
  useEffect(() => {
    let active = true;
    getSceneCaptions(scene.id).then(response => {
      if (!active) return;
      if (!response.ok) throw new Error(response.message || "Could not load captions.");
      setData(response.data);
      // Use the displayed precision on every boundary, including adjacent words.
      setWords(response.data.words.map(word => ({ ...word, start: Math.round(word.start * 1000) / 1000, end: Math.round(word.end * 1000) / 1000 })));
    }).catch(err => { if (active) setError(err.message || "Could not load captions. Close and reopen to try again."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [scene.id]);
  useEffect(() => {
    if (!playing) return;
    let frame, last = 0;
    const tick = now => {
      if (now - last >= 30) { setTime(player.current?.currentTime || 0); last = now; }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing]);
  const seek = seconds => { if (player.current) player.current.currentTime = seconds; setTime(seconds); };
  const save = async () => {
    if (saving.current || locked || !data) return;
    const issue = validateCaptionWords(words, data.duration);
    if (issue) { setError(issue); return; }
    saving.current = true; setBusy(true); setError("");
    try {
      const response = await updateSceneCaptions(scene.id, { words, revision: data.revision });
      if (!response.ok) { setError(response.message || "Could not save captions. Your changes are still here."); return; }
      onSaved(true); onClose();
    } catch { setError("Could not save captions. Your changes are still here; try again."); }
    finally { saving.current = false; setBusy(false); }
  };
  const visual = scene.scene_image?.file;
  return <EditorDialog open onClose={close} busy={busy} maxWidth="max-w-5xl" title={`Scene ${index + 1} captions`} description="Correct the words and their timing. Your recorded voice and dialogue stay the same." footer={<div className="flex justify-end gap-3"><button type="button" disabled={busy} onClick={close} className="rounded-xl px-4 py-3 text-sm text-gray-500 dark:text-gray-300">Cancel</button><button type="button" disabled={locked || !data || !dirty} onClick={save} className={editorButton}>{busy ? "Saving…" : "Save captions"}</button></div>}>
    {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-200">{error}</p>}
    {loading ? <p role="status">Loading captions…</p> : data && <>
      {!data.enabled && <p role="status" className="mb-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-900/20 dark:text-amber-200">Captions are off for this video. Enable Subtitles in video settings to show your saved captions in preview and export.</p>}
      <div className="grid items-start gap-6 md:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div className="md:sticky md:top-0">
          <div className={`relative mx-auto overflow-hidden rounded-xl bg-black ${size[1] > size[0] ? "w-40 md:w-full" : "w-full"}`} style={{ aspectRatio: `${size[0]} / ${size[1]}`, maxWidth: size[1] > size[0] ? 260 : undefined }}>
            {visual && (isVideo(visual) ? <video src={mediaUrl(visual)} muted playsInline preload="metadata" className="absolute inset-0 h-full w-full object-cover" /> : <img src={mediaUrl(visual)} alt={`Scene ${index + 1}`} className="absolute inset-0 h-full w-full object-cover" />)}
            <CaptionLayer cue={cue} style={data.style} size={size} config={data.config} />
          </div>
          <audio ref={player} controls preload="metadata" src={mediaUrl(data.audio)} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => setPlaying(false)} onError={() => setError("Could not play the source audio. Close and reopen the editor to try again.")} onTimeUpdate={event => setTime(event.currentTarget.currentTime)} onSeeked={event => setTime(event.currentTarget.currentTime)} className="mt-4 h-10 w-full" aria-label="Caption source narration" />
          <p className="mt-3 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Listen to the original voice audio while editing. Times start at the beginning of this audio, before trims and delays. Jump to a gap, then use Add word to insert a missing word. Saved captions follow those edits in the full video preview and export.</p>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{data.timing === "estimated" ? "These times are estimated. Adjust them while listening to the voice." : data.timing === "edited" ? "Your saved caption corrections." : "Word times measured from the spoken audio."} Save, then render again to update the finished video.</p>
        </div>
        <CaptionWordEditor words={words} onChange={next => { setWords(next); setDirty(true); }} duration={data.duration} time={time} disabled={locked} onSeek={seek} onError={setError} emptyMessage="No captions for this scene. Add words, or save to leave this scene without captions." />
      </div>
    </>}
  </EditorDialog>;
}
