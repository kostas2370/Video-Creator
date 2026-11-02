import { editorToolButton } from "./ui/editorStyles";
import { useEffect, useRef, useState } from "react";
import { FaPause, FaPlay } from "react-icons/fa";
import { HiOutlineArrowsPointingOut, HiOutlineArrowPath } from "react-icons/hi2";
import { EditorDialog, editorButton } from "./ui/EditorDialog";
import { API_HOST } from "../endpoints";
import { PhotoAnimationLayer } from "./PhotoAnimationLayer";
import { OverlayLayer } from "./OverlayLayer";
import { photoAnimationPlan, photoPresets } from "../utils/photoAnimation";
import { imageMotion, resolveImageMotion } from "../utils/motion";

export const hasStillImage = scene => /\.(png|jpe?g|webp)(?:[?#].*)?$/i.test(scene.scene_image?.file || "");

const styles = [["NONE", "No motion", "—"], ["AUTO", "Auto", "✦"], ["ZOOM_IN", "Zoom in", "+"], ["ZOOM_OUT", "Zoom out", "−"], ["PAN_LEFT", "Pan left", "←"], ["PAN_RIGHT", "Pan right", "→"], ["PAN_UP", "Pan up", "↑"], ["PAN_DOWN", "Pan down", "↓"]];
const intensities = [["SUBTLE", "Subtle"], ["MEDIUM", "Medium"], ["STRONG", "Strong"]];
const optionClass = selected => `rounded-xl border px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 disabled:opacity-40 ${selected ? "border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-400 dark:bg-blue-900/30 dark:text-blue-200" : "border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"}`;

export function SceneMotion({ scene, index, disabled, saving, onChange, videoFormat, fps = 24 }) {
  const [open, setOpen] = useState(false);
  const trigger = useRef(null);
  const close = () => { setOpen(false); requestAnimationFrame(() => trigger.current?.focus()); };
  const still = hasStillImage(scene);
  if (!still) return null;
  const presetLabel = photoPresets.find(([value]) => value === scene.animation_preset)?.[1];
  const label = presetLabel && scene.animation_preset !== "NONE" ? presetLabel : styles.find(([value]) => value === (scene.motion_style || "NONE"))?.[1] || "No motion";
  return <>
    <button ref={trigger} type="button" disabled={disabled} aria-label={`Edit motion for scene ${index + 1}`} onClick={() => setOpen(true)} className={editorToolButton}><HiOutlineArrowsPointingOut aria-hidden="true" className="h-5 w-5 shrink-0" />Animation · {label}</button>
    {open && <MotionEditor scene={scene} index={index} disabled={disabled} saving={saving} onChange={onChange} videoFormat={videoFormat} fps={fps} onClose={close} />}
  </>;
}

function MotionEditor({ scene, index, disabled, saving, onChange, videoFormat, fps, onClose }) {
  const [preset, setPreset] = useState(scene.animation_preset || "NONE");
  const [accents, setAccents] = useState(scene.animation_accents ?? true);
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
  const plan = photoAnimationPlan(preset, intensity, scene.id, accents);
  const stopped = style === "NONE" && preset === "NONE";
  const changed = preset !== (scene.animation_preset || "NONE") || accents !== (scene.animation_accents ?? true) || style !== (scene.motion_style || "NONE") || intensity !== (scene.motion_intensity || "SUBTLE");
  const locked = busy || saving;
  const restart = () => { timeRef.current = 0; setTime(0); setRestartVersion(value => value + 1); };
  useEffect(() => { timeRef.current = 0; setTime(0); }, [style, intensity, preset, accents]);
  useEffect(() => {
    if (!playing || stopped || imageFailed || locked) return;
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
  }, [playing, style, intensity, preset, stopped, duration, pause, imageFailed, locked, restartVersion]);
  const save = async () => {
    if (locked || disabled) return;
    setBusy(true); setError("");
    try {
      const saved = await onChange(scene, { motion_style: style, motion_intensity: intensity, animation_preset: preset, animation_accents: accents });
      if (saved) onClose();
      else setError("Could not save motion. Your choices are still here; try again.");
    } catch { setError("Could not save motion. Please try again."); }
    finally { setBusy(false); }
  };
  const frameClass = videoFormat === "PORTRAIT" ? "mx-auto aspect-[9/16] max-h-[330px] w-full max-w-[185px]" : videoFormat === "SQUARE" ? "mx-auto aspect-square w-full max-w-[330px]" : "aspect-video w-full";
  const file = scene.scene_image.file;
  const source = /^https?:\/\//i.test(file) ? file : `${API_HOST}${file}`;
  return <EditorDialog open onClose={onClose} title="Photo animation" description={`Scene ${index + 1} · Preview a preset or choose your own camera movement.`} busy={locked} footer={<div className="flex items-center justify-end gap-3"><button type="button" disabled={locked} onClick={onClose} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 disabled:opacity-40 dark:text-gray-300">Cancel</button><button type="button" onClick={save} disabled={locked || disabled || !changed} className={editorButton}>{locked ? "Saving…" : "Save animation"}</button></div>}>
    <div className="grid items-start gap-6 sm:grid-cols-2">
      <div>
        <div className={`relative overflow-hidden rounded-xl bg-gray-100 dark:bg-gray-900 ${frameClass}`}>
          {imageFailed ? <p role="status" className="flex h-full items-center justify-center p-4 text-center text-sm text-gray-500">Could not load the preview image.</p> : <img alt={`Scene ${index + 1} motion preview`} src={source} onError={() => setImageFailed(true)} style={imageMotion({ motion_style: resolved, motion_intensity: intensity, base_duration: duration, fps, photo_animation: plan }, time)} className="absolute inset-0 h-full w-full object-cover" />}
          {!imageFailed && <><PhotoAnimationLayer plan={plan} time={time} duration={duration} fps={fps} /><OverlayLayer overlays={scene.overlays?.length ? scene.overlays : preset !== "NONE" ? [{ text: "Your visual story", size: 6, color: "#ffffff", background: true, opacity: 1, position: "middle-center", start: 0, end: null }] : []} logo={scene.overlay_logo} time={time} duration={duration + pause} frameSize={videoFormat === "PORTRAIT" ? [1080, 1920] : videoFormat === "SQUARE" ? [1080, 1080] : [1920, 1080]} animationPreset={preset} /></>}
        </div>
        <div className="mt-3 flex items-center justify-between gap-2">
          <p className="text-xs text-gray-500 dark:text-gray-400">{stopped ? "Still image" : !playing ? "Preview paused" : time >= duration && pause > 0 ? "Holding final frame" : "Looping preview"}</p>
          <div className="flex gap-1"><button type="button" aria-label={playing ? "Pause motion preview" : "Play motion preview"} disabled={stopped || imageFailed || locked} onClick={() => setPlaying(value => !value)} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 disabled:opacity-40 dark:text-gray-300 dark:hover:bg-gray-700">{playing ? <FaPause /> : <FaPlay />}</button><button type="button" aria-label="Restart motion preview" disabled={stopped || imageFailed || locked} onClick={restart} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 disabled:opacity-40 dark:text-gray-300 dark:hover:bg-gray-700"><HiOutlineArrowPath className="h-4 w-4" /></button></div>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">{preset === "NONE" && style === "AUTO" ? `Auto uses ${styles.find(([value]) => value === resolved)?.[1].toLowerCase()} for this scene. ` : ""}Changes apply after you save. Render again to export. The sample label is only a preview when no overlays exist.</p>
      </div>
      <div>
        <PresetPicker preset={preset} setPreset={setPreset} accents={accents} setAccents={setAccents} disabled={locked || disabled} />
        {preset === "NONE" && <fieldset disabled={locked || disabled} className="mt-5"><legend className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">Camera movement</legend><div className="grid grid-cols-2 gap-2">{styles.map(([value, label, icon]) => <button type="button" key={value} aria-pressed={style === value} onClick={() => setStyle(value)} className={`${optionClass(style === value)} flex items-center gap-2`}><span aria-hidden="true" className="w-4 text-center text-lg">{icon}</span>{label}</button>)}</div></fieldset>}
        <fieldset disabled={locked || disabled || stopped} className="mt-5"><legend className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">Intensity</legend><div className="grid grid-cols-3 gap-2">{intensities.map(([value, label]) => <button type="button" key={value} aria-pressed={intensity === value} onClick={() => setIntensity(value)} className={optionClass(intensity === value)}>{label}</button>)}</div></fieldset>
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
    <button ref={trigger} type="button" disabled={disabled || !count} onClick={() => setOpen(true)} className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 disabled:opacity-40 dark:border-gray-700 dark:bg-gray-800 dark:text-blue-400 dark:hover:bg-gray-700"><span aria-hidden="true">✦</span>Animate all photos</button>
    {open && <BulkAutoEditor count={count} disabled={disabled} saving={saving} onApply={onApply} onClose={close} />}
  </>;
}

function BulkAutoEditor({ count, disabled, saving, onApply, onClose }) {
  const [preset, setPreset] = useState("PLAYFUL");
  const [accents, setAccents] = useState(true);
  const [intensity, setIntensity] = useState("SUBTLE");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const locked = busy || saving;
  const apply = async () => {
    if (locked || disabled || !count) return;
    setBusy(true); setError("");
    try {
      if (await onApply(intensity, preset, accents)) onClose();
      else setError("Could not apply animations. Please try again.");
    } catch { setError("Could not apply animations. Please try again."); }
    finally { setBusy(false); }
  };
  return <EditorDialog open onClose={onClose} title="Animate all photos" description={`Apply to ${count} image ${count === 1 ? "scene" : "scenes"}.`} busy={locked} footer={<div className="flex justify-end gap-3"><button type="button" disabled={locked} onClick={onClose} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 disabled:opacity-40 dark:text-gray-300">Cancel</button><button type="button" disabled={locked || disabled || !count} onClick={apply} className={editorButton}>{locked ? "Applying…" : "Apply animation"}</button></div>}>
    <p className="text-sm leading-relaxed text-gray-600 dark:text-gray-300">Choose a reusable style for your photo scenes. This replaces their current animation settings. Video clips keep their existing appearance. Camera only applies varied zooms and pans.</p>
    <div className="mt-5"><PresetPicker preset={preset} setPreset={setPreset} accents={accents} setAccents={setAccents} disabled={locked || disabled} /></div>
    <fieldset disabled={locked || disabled} className="mt-5"><legend className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">Intensity</legend><div className="grid grid-cols-3 gap-2">{intensities.map(([value, label]) => <button type="button" key={value} aria-pressed={intensity === value} onClick={() => setIntensity(value)} className={optionClass(intensity === value)}>{label}</button>)}</div></fieldset>
    <p className="mt-4 text-xs text-gray-500 dark:text-gray-400">You can adjust individual scenes afterward. Preview your video, then render again to export.</p>
    {error && <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>}
  </EditorDialog>;
}

function PresetPicker({ preset, setPreset, accents, setAccents, disabled }) {
  return <fieldset disabled={disabled}>
    <legend className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">Animation style</legend>
    <div className="grid grid-cols-2 gap-2">{photoPresets.map(([value, label, description]) => <button type="button" key={value} aria-pressed={preset === value} onClick={() => setPreset(value)} className={`${optionClass(preset === value)} text-left`}><span className="block">{label}</span><span className="mt-1 block text-xs font-normal">{description}</span></button>)}</div>
    {preset !== "NONE" && preset !== "EXPLAINER" && <label className="mt-3 flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300"><input type="checkbox" checked={accents} onChange={event => setAccents(event.target.checked)} />Decorative particles</label>}
    <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">Uses your existing photos. No AI video generation needed. Add text in Text & logos to animate labels and titles.</p>
  </fieldset>;
}
