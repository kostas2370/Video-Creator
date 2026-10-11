import React, { useCallback, useEffect, useId, useRef, useState, memo } from "react";
import { FaPause, FaPlay, FaUndo, FaVolumeMute, FaVolumeUp } from "react-icons/fa";
import { Dialog, DialogBackdrop, DialogPanel, DialogTitle, Description } from "@headlessui/react";
import { HiOutlineXMark } from "react-icons/hi2";
import { getVideoPreview } from "../api/apiService";
import { API_HOST } from "../endpoints";

const mediaUrl = url => /^https?:\/\//i.test(url || "") ? url : `${API_HOST}${url}`;
const clock = seconds => `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;

// The global clock owns playback. Media readers follow it and stop during held frames.
function Track({ source, video = false, time, duration, playing, muted, onFailure, onBlocked, onBuffering, stalled, seekVersion }) {
  const ref = useRef(null);
  const starting = useRef(false);
  const trackId = useId();
  const position = useRef(time);
  const lastSeek = useRef(-1);
  const pendingSeek = useRef(false);
  position.current = time;
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const sync = (force = false) => {
      if (force) pendingSeek.current = true;
      const time = position.current;
      const length = Number.isFinite(element.duration) ? element.duration : duration;
      const end = Math.max(0, (length || 0) - (video ? 1 / 24 : 0.01));
      const target = Math.min(Math.max(0, time), end);
      // Let native playback advance; seeking repeatedly can restart decoding and buffering.
      const tolerance = pendingSeek.current || !playing ? 0.01 : video ? 0.5 : 0.2;
      if (!element.seeking) {
        if ((!stalled || pendingSeek.current) && Math.abs(element.currentTime - target) > tolerance) element.currentTime = target;
        pendingSeek.current = false;
      }
      const active = playing && !stalled && time < (length || duration || 0) && (video || !muted);
      if (active && element.paused && !starting.current) {
        starting.current = true;
        element.play().catch(error => {
          if (error.name === "NotAllowedError") onBlocked();
          else if (error.name !== "AbortError") onFailure();
        }).finally(() => { starting.current = false; });
      }
      else if (!active) element.pause();
    };
    const align = () => sync(true);
    const afterSeek = () => { if (pendingSeek.current) sync(true); };
    // Explicit seeks and playback changes align immediately; drift checks run four times per second.
    sync(lastSeek.current !== seekVersion);
    lastSeek.current = seekVersion;
    const interval = playing ? setInterval(sync, 250) : null;
    element.addEventListener("loadedmetadata", align);
    element.addEventListener("seeked", afterSeek);
    return () => {
      clearInterval(interval);
      element.removeEventListener("loadedmetadata", align);
      element.removeEventListener("seeked", afterSeek);
    };
  }, [duration, playing, muted, video, onFailure, onBlocked, stalled, seekVersion]);
  useEffect(() => {
    const element = ref.current;
    return () => { element?.pause(); onBuffering(trackId, false); };
  }, [source, onBuffering, trackId]);
  const props = { ref, src: mediaUrl(source), muted, preload: "auto", onError: () => { onBuffering(trackId, false); onFailure(); }, onWaiting: event => { if (playing && time < (event.currentTarget.duration || duration || 0) && (video || !muted)) onBuffering(trackId, true); }, onCanPlay: () => onBuffering(trackId, false) };
  return video ? <video {...props} playsInline className="absolute inset-0 h-full w-full object-cover" /> : <audio {...props} />;
}

function Visual({ segment, time, playing, muted, onFailure, onBlocked, opacity = 1, onBuffering, stalled, seekVersion }) {
  if (!segment?.visual) return <div className="absolute inset-0 flex items-center justify-center bg-black px-5 text-center text-sm text-gray-400">No visual available</div>;
  return <div className="absolute inset-0" style={{ opacity }}>
    {segment.visual_type === "video" ? <Track source={segment.visual} video time={time} duration={segment.visual_duration} playing={playing} muted={muted || !segment.clip_audio} onFailure={onFailure} onBlocked={onBlocked} onBuffering={onBuffering} stalled={stalled} seekVersion={seekVersion} />
      : <img src={mediaUrl(segment.visual)} alt={segment.label} onError={onFailure} className="absolute inset-0 h-full w-full object-cover" />}
  </div>;
}

export function VideoPreviewModal({ open, onClose, video, disabled = false }) {
  if (!open || !video) return null;
  return <Dialog open={open} onClose={onClose} className="relative z-50">
    <DialogBackdrop className="fixed inset-0 bg-gray-950/70 backdrop-blur-sm" />
    <div className="fixed inset-0 flex items-center justify-center p-3 sm:p-6">
      <DialogPanel className="flex max-h-[calc(100dvh-1.5rem)] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl dark:border-gray-700 dark:bg-gray-900 sm:max-h-[calc(100dvh-3rem)]">
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-gray-100 px-4 py-4 dark:border-gray-800 sm:px-6">
          <div className="min-w-0">
            <DialogTitle className="text-lg font-semibold text-gray-900 dark:text-white">Preview video</DialogTitle>
            <p className="mt-1 truncate text-sm text-gray-700 dark:text-gray-300">{video.title}</p>
            <Description className="mt-1 text-xs text-gray-500 dark:text-gray-400">Watch your saved edits before rendering.</Description>
          </div>
          <button type="button" data-autofocus aria-label="Close preview" onClick={onClose} className="shrink-0 rounded-full p-2 text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:hover:bg-gray-800"><HiOutlineXMark aria-hidden="true" className="h-5 w-5" /></button>
        </header>
        <div className="min-h-0 overflow-y-auto p-4 sm:p-6"><VideoPreview video={video} disabled={disabled} /></div>
      </DialogPanel>
    </div>
  </Dialog>;
}

function VideoPreview({ video, disabled = false }) {
  const [manifest, setManifest] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mediaError, setMediaError] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [waiting, setWaiting] = useState({});
  const buffering = Object.values(waiting).some(Boolean);
  const onBuffering = useCallback((source, value) => setWaiting(current => current[source] === value ? current : { ...current, [source]: value }), []);
  const [muted, setMuted] = useState(false);
  const [time, setTime] = useState(0);
  const [seekVersion, setSeekVersion] = useState(0);
  const [retry, setRetry] = useState(0);
  const anchor = useRef({ position: 0, wall: 0 });
  const timeRef = useRef(0);
  const activeButton = useRef(null);
  const timeline = useRef(null);
  const allowed = ["READY", "COMPLETED", "FAILED"].includes(video?.status);
  // Polling returns new objects even when nothing changed; only an edited timeline reloads.
  const revision = JSON.stringify([video?.id, video?.status, video?.updated_at, video?.settings,
    video?.intro, video?.outro, video?.avatar, video?.music, video?.background,
    video?.scenes?.map(s => [s.id, s.text, s.file, s.scene_image, s.timing, s.pause_after, s.transition_after, s.transition_duration])]);
  useEffect(() => {
    setPlaying(false);
    setManifest(null);
    setTime(0);
    timeRef.current = 0;
    if (!allowed || disabled) return;
    let current = true;
    setLoading(true); setError(""); setMediaError(false);
    getVideoPreview(video.id).then(response => {
      if (!current) return;
      if (!response.ok || !response.data?.segments?.length || !(response.data.duration > 0)) setError(response.message || "Preview is unavailable. Check your scene media and try again.");
      else setManifest(response.data);
      setLoading(false);
    }).catch(() => { if (current) { setError("Could not load the preview. Please try again."); setLoading(false); } });
    return () => { current = false; };
  }, [revision, allowed, disabled, retry, video?.id]);
  useEffect(() => {
    if (!playing || !manifest || buffering) return;
    let frame;
    let lastUpdate = 0;
    anchor.current = { position: timeRef.current, wall: performance.now() };
    const tick = now => {
      const next = Math.min(manifest.duration, anchor.current.position + (now - anchor.current.wall) / 1000);
      timeRef.current = next;
      // Keep the UI responsive without rendering every browser animation frame.
      if (now - lastUpdate >= 1000 / 30 || next >= manifest.duration) {
        setTime(next);
        lastUpdate = now;
      }
      if (next >= manifest.duration) setPlaying(false);
      else frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, manifest, buffering]);
  useEffect(() => {
    const pauseHidden = () => { if (document.hidden) setPlaying(false); };
    document.addEventListener("visibilitychange", pauseHidden);
    return () => document.removeEventListener("visibilitychange", pauseHidden);
  }, []);
  const seek = useCallback(position => {
    const next = Math.max(0, Math.min(manifest?.duration || 0, position));
    anchor.current = { position: next, wall: performance.now() };
    timeRef.current = next;
    setTime(next);
    setSeekVersion(version => version + 1);
  }, [manifest?.duration]);
  const failMedia = useCallback(() => setMediaError(true), []);
  const blocked = useCallback(() => { setPlaying(false); setError("Your browser paused the media. Press play to try again."); }, []);
  const segments = manifest?.segments || [];
  const index = Math.max(0, segments.findIndex(segment => time < segment.start + segment.duration));
  const active = time >= (manifest?.duration || Infinity) ? segments[segments.length - 1] : segments[index];
  const local = active ? Math.min(time - active.start, active.duration) : 0;
  const previous = segments[index - 1];
  const dissolve = active?.dissolve_in > 0 && local < active.dissolve_in && previous;
  let opacity = 1;
  if (active?.fade_in && local < active.fade_in) opacity = local / active.fade_in;
  if (active?.fade_out && local > active.duration - active.fade_out) opacity = Math.min(opacity, (active.duration - local) / active.fade_out);
  const cue = manifest?.captions?.find(c => time >= c.start && time < c.end);
  const activeId = active?.id;
  useEffect(() => {
    if (!activeButton.current || !timeline.current) return;
    const keepActiveVisible = () => {
      if (!activeButton.current || !timeline.current) return;
      const button = activeButton.current.getBoundingClientRect();
      const strip = timeline.current.getBoundingClientRect();
      if (button.left < strip.left) timeline.current.scrollLeft += button.left - strip.left;
      else if (button.right > strip.right) timeline.current.scrollLeft += button.right - strip.right;
    };
    keepActiveVisible();
    const observer = new ResizeObserver(keepActiveVisible);
    observer.observe(timeline.current);
    return () => observer.disconnect();
  }, [activeId]);

  return <section aria-label="Preview player" className="min-w-0">
    {active && <div className="mb-3 flex justify-end"><span aria-live="polite" className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">{active.label}{local >= active.base_duration && active.pause > 0 ? " · Pause" : ""}</span></div>}
    {!allowed || disabled ? <p role="status" className="rounded-xl bg-gray-50 p-4 text-sm text-gray-500 dark:bg-gray-900/40 dark:text-gray-400">{disabled ? "Preview updates once your changes are saved." : "Preview becomes available when scene processing finishes."}</p> : loading ? <p role="status" className="py-8 text-center text-sm text-gray-500">Loading preview…</p> : <>
      {error && <div role="alert" className="mb-3 flex flex-wrap items-center gap-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-900/20 dark:text-amber-200"><span>{error}</span><button type="button" onClick={() => setRetry(value => value + 1)} className="font-semibold underline">Reload preview</button></div>}
      {manifest && <>
        <div className="mx-auto w-full max-w-2xl overflow-hidden rounded-xl bg-black" style={{ maxWidth: manifest.size[0] < manifest.size[1] ? 280 : manifest.size[0] === manifest.size[1] ? 420 : undefined }}>
          <div role="img" aria-label={`${active?.label || "Video"} preview`} className="relative isolate w-full overflow-hidden bg-black" style={{ aspectRatio: `${manifest.size[0]} / ${manifest.size[1]}` }}>
            {active && <Visual key={active.id} segment={active} time={local} playing={playing} muted={muted} opacity={time === 0 && !playing ? 1 : Math.max(0, opacity)} onFailure={failMedia} onBlocked={blocked} onBuffering={onBuffering} stalled={buffering} seekVersion={seekVersion} />}
            {dissolve && <Visual key={`hold-${previous.id}`} segment={previous} time={previous.duration} playing={false} muted opacity={1 - local / active.dissolve_in} onFailure={failMedia} onBlocked={blocked} onBuffering={onBuffering} stalled={buffering} seekVersion={seekVersion} />}
            {active?.narration && <Track key={`voice-${active.id}`} source={active.narration} time={local} duration={active.narration_duration} playing={playing} muted={muted} onFailure={failMedia} onBlocked={blocked} onBuffering={onBuffering} stalled={buffering} seekVersion={seekVersion} />}
            {cue && <div data-preview-caption className="pointer-events-none absolute inset-x-[8%] bottom-[5%] z-10 whitespace-pre-line rounded bg-black/60 px-2 py-1 text-center font-semibold leading-snug text-white" style={{ fontSize: "clamp(12px, 2vw, 22px)", textShadow: "0 1px 2px black" }}>{cue.text}</div>}
          </div>
        </div>
        <div className="mt-4 flex items-center gap-2 sm:gap-3">
          <button type="button" aria-label={playing ? "Pause preview" : "Play preview"} onClick={() => { setError(""); if (time >= manifest.duration) seek(0); setPlaying(value => !value); }} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white hover:bg-blue-700">{playing ? <FaPause /> : <FaPlay />}</button>
          <button type="button" aria-label="Restart preview" onClick={() => seek(0)} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"><FaUndo /></button>
          <input aria-label="Preview playhead" type="range" min="0" max={manifest.duration} step="0.01" value={time} onChange={event => seek(Number(event.target.value))} className="min-w-0 flex-1 accent-blue-600" />
          <span className="shrink-0 text-xs tabular-nums text-gray-500 dark:text-gray-300">{clock(time)} / {clock(manifest.duration)}</span>
          <button type="button" aria-label={muted ? "Unmute preview" : "Mute preview"} onClick={() => setMuted(value => !value)} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700">{muted ? <FaVolumeMute /> : <FaVolumeUp />}</button>
        </div>
        <h2 className="mt-5 text-sm font-semibold text-gray-900 dark:text-white">Scene timeline</h2>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Choose a scene to jump to it.</p>
        <Timeline segments={segments} activeId={activeId} local={local} activeButton={activeButton} timelineRef={timeline} onSeek={seek} />
        {buffering && <p role="status" className="mt-2 text-xs text-gray-500">Buffering preview…</p>}
        {mediaError && <p role="status" className="mt-2 text-xs text-amber-700 dark:text-amber-300">Some media could not load. Check the scene files or reload the preview.</p>}
        <details className="mt-3 text-xs leading-relaxed text-gray-500 dark:text-gray-400"><summary className="cursor-pointer font-medium">About this preview</summary><p className="mt-2">No rendering or generation credits required. Caption timing is estimated; caption appearance may vary in the render.{manifest.render_only?.length > 0 ? ` Render to include ${manifest.render_only.join(", ")}.` : ""}</p></details>
      </>}
    </>}
  </section>;
}

const TimelineItem = memo(function TimelineItem({ segment, active, progress, activeButton, onSeek }) {
  return <button type="button" ref={active ? activeButton : null} aria-label={`Preview ${segment.label}`} aria-current={active ? "true" : undefined} onClick={() => onSeek(segment.start)} style={{ width: Math.max(100, Math.min(240, segment.duration * 18)) }} className={`relative shrink-0 overflow-hidden rounded-xl border-2 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 ${active ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20" : "border-gray-200 dark:border-gray-700"}`}>
              <div className="relative h-14 overflow-hidden bg-gray-100 dark:bg-gray-900">{segment.visual && (segment.visual_type === "video" ? <video src={mediaUrl(segment.visual)} muted playsInline preload="metadata" className="h-full w-full object-cover" /> : <img src={mediaUrl(segment.visual)} alt="" className="h-full w-full object-cover" />)}{!segment.visual && <span className="flex h-full items-center justify-center text-xs text-gray-400">No visual</span>}</div>
              <div className="px-2 py-1.5"><span className="block text-xs font-semibold text-gray-700 dark:text-gray-200">{segment.label}</span><span className="block text-[11px] text-gray-500 dark:text-gray-400">{segment.duration.toFixed(1)}s{segment.pause > 0 ? ` · +${segment.pause}s pause` : ""}</span></div>
              {active && <span aria-hidden="true" className="pointer-events-none absolute bottom-0 top-0 w-0.5 bg-blue-500" style={{ left: `${Math.min(100, Math.max(0, progress / segment.duration * 100))}%` }} />}
            </button>;
});

function Timeline({ segments, activeId, local, activeButton, timelineRef, onSeek }) {
  return <nav ref={timelineRef} aria-label="Preview timeline" className="mt-3 flex gap-2 overflow-x-auto pb-2">
          {segments.map((segment, segmentIndex) => <React.Fragment key={segment.id}>
            <TimelineItem segment={segment} active={segment.id === activeId} progress={segment.id === activeId ? local : 0} activeButton={activeButton} onSeek={onSeek} />
            {segmentIndex < segments.length - 1 && <span className="flex shrink-0 items-center text-[10px] text-gray-400">{segment.kind === "scene" && segments[segmentIndex + 1].kind === "scene" ? ({ CUT: "Cut", FADE: "Fade", DISSOLVE: "Dissolve" }[segment.transition]) : "Cut"}</span>}
          </React.Fragment>)}
        </nav>;
}
