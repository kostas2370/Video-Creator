import { useEffect, useRef, useState } from "react";
import { FaPause, FaPlay } from "react-icons/fa";
import { HiOutlineArrowsPointingOut, HiOutlineArrowPath } from "react-icons/hi2";
import { EditorDialog, editorButton } from "./ui/EditorDialog";
import { API_HOST } from "../endpoints";
import { imageMotion, resolveImageMotion } from "../utils/motion";

export const hasStillImage = scene => /\.(png|jpe?g)(?:[?#].*)?$/i.test(scene.scene_image?.file || "");

const styles = [["NONE", "No motion", "—"], ["AUTO", "Auto", "✦"], ["ZOOM_IN", "Zoom in", "+"], ["ZOOM_OUT", "Zoom out", "−"], ["PAN_LEFT", "Pan left", "←"], ["PAN_RIGHT", "Pan right", "→"], ["PAN_UP", "Pan up", "↑"], ["PAN_DOWN", "Pan down", "↓"]];
const intensities = [["SUBTLE", "Subtle"], ["MEDIUM", "Medium"], ["STRONG", "Strong"]];
const optionClass = selected => `rounded-xl border px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 disabled:opacity-40 ${selected ? "border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-400 dark:bg-blue-900/30 dark:text-blue-200" : "border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"}`;

export function SceneMotion({ scene, index, disabled, saving, onChange, videoFormat }) {
  const [open, setOpen] = useState(false);
  const trigger = useRef(null);
  const close = () => { setOpen(false); requestAnimationFrame(() => trigger.current?.focus()); };
  const still = hasStillImage(scene);
  if (!still) return null;
  const label = styles.find(([value]) => value === (scene.motion_style || "NONE"))?.[1] || "No motion";
  return <>
    <button ref={trigger} type="button" disabled={disabled} aria-label={`Edit motion for scene ${index + 1}`} onClick={() => setOpen(true)} className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-medium text-blue-600 hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-40 dark:text-blue-400 dark:hover:bg-gray-700"><HiOutlineArrowsPointingOut aria-hidden="true" className="h-4 w-4" />Motion · {label}</button>
    {open && <MotionEditor scene={scene} index={index} disabled={disabled} saving={saving} onChange={onChange} videoFormat={videoFormat} onClose={close} />}
  </>;
}

function MotionEditor({ scene, index, disabled, saving, onChange, videoFormat, onClose }) {
  const [style, setStyle] = useState(scene.motion_style || "NONE");
  const [intensity, setIntensity] = useState(scene.motion_intensity || "SUBTLE");
  const [playing, setPlaying] = useState(() => !window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [time, setTime] = useState(0);
  const [restartVersion, setRestartVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [imageFailed, setImageFailed] = useState(false);
  const timeRef = useRef(0);
  const duration = scene.timing?.base_duration > 0 ? scene.timing.base_duration : 5;
  const pause = scene.pause_after || 0;
  const resolved = resolveImageMotion(style, scene.id);
  const changed = style !== (scene.motion_style || "NONE") || intensity !== (scene.motion_intensity || "SUBTLE");
  const locked = busy || saving;
  const restart = () => { timeRef.current = 0; setTime(0); setRestartVersion(value => value + 1); };
  useEffect(() => { timeRef.current = 0; setTime(0); }, [style, intensity]);
  useEffect(() => {
    if (!playing || style === "NONE" || imageFailed || locked) return;
    let frame;
    const anchor = performance.now() - timeRef.current * 1000;
    const tick = now => {
      const next = ((now - anchor) / 1000) % (duration + pause + 0.5);
      timeRef.current = next;
      setTime(next);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, style, intensity, duration, pause, imageFailed, locked, restartVersion]);
  const save = async () => {
    if (locked || disabled) return;
    setBusy(true); setError("");
    try {
      const saved = await onChange(scene, { motion_style: style, motion_intensity: intensity });
      if (saved) onClose();
      else setError("Could not save motion. Your choices are still here; try again.");
    } catch { setError("Could not save motion. Please try again."); }
    finally { setBusy(false); }
  };
  const frameClass = videoFormat === "PORTRAIT" ? "mx-auto aspect-[9/16] max-h-[330px] w-full max-w-[185px]" : videoFormat === "SQUARE" ? "mx-auto aspect-square w-full max-w-[330px]" : "aspect-video w-full";
  const file = scene.scene_image.file;
  const source = /^https?:\/\//i.test(file) ? file : `${API_HOST}${file}`;
  return <EditorDialog open onClose={onClose} title="Scene motion" description={`Scene ${index + 1} · Try a movement before saving.`} busy={locked} footer={<div className="flex items-center justify-end gap-3"><button type="button" disabled={locked} onClick={onClose} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 disabled:opacity-40 dark:text-gray-300">Cancel</button><button type="button" onClick={save} disabled={locked || disabled || !changed} className={editorButton}>{locked ? "Saving…" : "Save motion"}</button></div>}>
    <div className="grid items-start gap-6 sm:grid-cols-2">
      <div>
        <div className={`relative overflow-hidden rounded-xl bg-gray-100 dark:bg-gray-900 ${frameClass}`}>
          {imageFailed ? <p role="status" className="flex h-full items-center justify-center p-4 text-center text-sm text-gray-500">Could not load the preview image.</p> : <img alt={`Scene ${index + 1} motion preview`} src={source} onError={() => setImageFailed(true)} style={imageMotion({ motion_style: resolved, motion_intensity: intensity, base_duration: duration }, time)} className="absolute inset-0 h-full w-full object-cover" />}
        </div>
        <div className="mt-3 flex items-center justify-between gap-2">
          <p className="text-xs text-gray-500 dark:text-gray-400">{style === "NONE" ? "Still image" : !playing ? "Preview paused" : time >= duration && pause > 0 ? "Holding final frame" : "Looping preview"}</p>
          <div className="flex gap-1"><button type="button" aria-label={playing ? "Pause motion preview" : "Play motion preview"} disabled={style === "NONE" || imageFailed || locked} onClick={() => setPlaying(value => !value)} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 disabled:opacity-40 dark:text-gray-300 dark:hover:bg-gray-700">{playing ? <FaPause /> : <FaPlay />}</button><button type="button" aria-label="Restart motion preview" disabled={style === "NONE" || imageFailed || locked} onClick={restart} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 disabled:opacity-40 dark:text-gray-300 dark:hover:bg-gray-700"><HiOutlineArrowPath className="h-4 w-4" /></button></div>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">{style === "AUTO" ? `Auto uses ${styles.find(([value]) => value === resolved)?.[1].toLowerCase()} for this scene. ` : ""}Changes apply after you save. Render again to export.</p>
      </div>
      <div>
        <fieldset disabled={locked || disabled}><legend className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">Movement</legend><div className="grid grid-cols-2 gap-2">{styles.map(([value, label, icon]) => <button type="button" key={value} aria-pressed={style === value} onClick={() => setStyle(value)} className={`${optionClass(style === value)} flex items-center gap-2`}><span aria-hidden="true" className="w-4 text-center text-lg">{icon}</span>{label}</button>)}</div></fieldset>
        <fieldset disabled={locked || disabled || style === "NONE"} className="mt-5"><legend className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">Intensity</legend><div className="grid grid-cols-3 gap-2">{intensities.map(([value, label]) => <button type="button" key={value} aria-pressed={intensity === value} onClick={() => setIntensity(value)} className={optionClass(intensity === value)}>{label}</button>)}</div></fieldset>
        {error && <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>}
      </div>
    </div>
  </EditorDialog>;
}

export function BulkAutoMotion({ scenes, disabled, saving, onApply }) {
  const [open, setOpen] = useState(false);
  const trigger = useRef(null);
  const count = scenes.filter(hasStillImage).length;
  const close = () => { setOpen(false); requestAnimationFrame(() => trigger.current?.focus()); };
  return <>
    <button ref={trigger} type="button" disabled={disabled || !count} onClick={() => setOpen(true)} className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 disabled:opacity-40 dark:border-gray-700 dark:bg-gray-800 dark:text-blue-400 dark:hover:bg-gray-700"><span aria-hidden="true">✦</span>Apply Auto to all images</button>
    {open && <BulkAutoEditor count={count} disabled={disabled} saving={saving} onApply={onApply} onClose={close} />}
  </>;
}

function BulkAutoEditor({ count, disabled, saving, onApply, onClose }) {
  const [intensity, setIntensity] = useState("SUBTLE");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const locked = busy || saving;
  const apply = async () => {
    if (locked || disabled || !count) return;
    setBusy(true); setError("");
    try {
      if (await onApply(intensity)) onClose();
      else setError("Could not apply Auto. Please try again.");
    } catch { setError("Could not apply Auto. Please try again."); }
    finally { setBusy(false); }
  };
  return <EditorDialog open onClose={onClose} title="Auto motion for all images" description={`Apply to ${count} image ${count === 1 ? "scene" : "scenes"}.`} busy={locked} footer={<div className="flex justify-end gap-3"><button type="button" disabled={locked} onClick={onClose} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 disabled:opacity-40 dark:text-gray-300">Cancel</button><button type="button" disabled={locked || disabled || !count} onClick={apply} className={editorButton}>{locked ? "Applying…" : "Apply Auto"}</button></div>}>
    <p className="text-sm leading-relaxed text-gray-600 dark:text-gray-300">Auto assigns each image a zoom or pan and keeps that movement consistent. This replaces existing motion choices on image scenes. Video clips stay as they are.</p>
    <fieldset disabled={locked || disabled} className="mt-5"><legend className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">Intensity</legend><div className="grid grid-cols-3 gap-2">{intensities.map(([value, label]) => <button type="button" key={value} aria-pressed={intensity === value} onClick={() => setIntensity(value)} className={optionClass(intensity === value)}>{label}</button>)}</div></fieldset>
    <p className="mt-4 text-xs text-gray-500 dark:text-gray-400">You can adjust individual scenes afterward. Preview your video, then render again to export.</p>
    {error && <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>}
  </EditorDialog>;
}
