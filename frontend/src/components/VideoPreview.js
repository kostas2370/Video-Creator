import { DeferredVideo } from "./ui/DeferredVideo";
import { OverlayLayer } from "./OverlayLayer";
import { PhotoAnimationLayer } from "./PhotoAnimationLayer";
import { CaptionLayer } from "./CaptionLayer";
import React, { useCallback, useEffect, useId, useRef, useState, useMemo, memo } from "react";
import { FaPause, FaPlay, FaUndo, FaVolumeMute, FaVolumeUp } from "react-icons/fa";
import { HiOutlinePlay } from "react-icons/hi2";
import { EditorDialog, editorSecondaryButton } from "./ui/EditorDialog";
import { getVideoPreview } from "../api/apiService";
import { API_HOST } from "../endpoints";
import { voiceGain, musicGain } from "./audioEnvelope";

import { joinedPosition, sourcePosition, sectionsDuration, previewSections, cutClock } from "../utils/cuts";
import { imageMotion } from "../utils/motion";

const mediaUrl = url => /^https?:\/\//i.test(url || "") ? url : `${API_HOST}${url}`;
const clock = seconds => `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;

// The global clock owns playback. Media readers follow it and stop during held frames.
export function Track({ source, video = false, time, duration, playing, muted, onFailure, onBlocked, onBuffering, stalled, seekVersion, trimStart = 0, loop = false, volume = 1 }) {
  const ref = useRef(null);
  const starting = useRef(false);
  const synchronize = useRef(null);
  const trackId = useId();
  const position = useRef(time);
  const lastSeek = useRef(-1);
  const pendingSeek = useRef(false);
  position.current = time;
  const gain = useRef(volume);
  gain.current = volume;
  useEffect(() => { if (ref.current) ref.current.volume = Math.max(0, Math.min(1, volume)); }, [volume]);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const sync = (force = false) => {
      if (force) pendingSeek.current = true;
      const time = position.current;
      const length = Number.isFinite(element.duration) ? element.duration : duration;
      const end = Math.max(0, (length || 0) - (video ? 1 / 24 : 0.01));
      const target = loop && length > 0 ? Math.max(0, time) % length : Math.min(Math.max(0, time) + trimStart, end);
      element.volume = Math.max(0, Math.min(1, gain.current));
      // Let native playback advance; seeking repeatedly can restart decoding and buffering.
      const tolerance = pendingSeek.current ? 0.01 : video ? 0.5 : 0.2;
      const shouldAlign = pendingSeek.current || (playing && !stalled && !element.paused && !starting.current);
      if (!element.seeking) {
        if (shouldAlign && Math.abs(element.currentTime - target) > tolerance) element.currentTime = target;
        pendingSeek.current = false;
      }
      const requested = playing && time >= 0 && time < (duration || length || 0)
        && (loop || (!element.ended && target < end)) && (video || !muted);
      const waitingForMedia = requested && (element.readyState < 3 || element.seeking);
      onBuffering(trackId, waitingForMedia);
      const active = requested && !stalled && !waitingForMedia;
      if (active && element.paused && !starting.current) {
        starting.current = true;
        element.play().catch(error => {
          if (error.name === "NotAllowedError") onBlocked();
          else if (error.name !== "AbortError") onFailure();
        }).finally(() => {
          starting.current = false;
          // A quick pause/resume can replace this effect before play() settles.
          // Resume immediately instead of waiting for the next drift check.
          if (synchronize.current && synchronize.current !== sync) synchronize.current();
        });
      }
      else if (!active) element.pause();
    };
    synchronize.current = sync;
    const align = () => sync(true);
    const afterSeek = () => sync(pendingSeek.current);
    const ready = () => sync();
    // Explicit seeks and playback changes align immediately; drift checks run four times per second.
    sync(lastSeek.current !== seekVersion);
    lastSeek.current = seekVersion;
    const interval = playing ? setInterval(sync, 250) : null;
    element.addEventListener("loadedmetadata", align);
    element.addEventListener("seeked", afterSeek);
    element.addEventListener("canplay", ready);
    return () => {
      if (synchronize.current === sync) synchronize.current = null;
      clearInterval(interval);
      element.removeEventListener("loadedmetadata", align);
      element.removeEventListener("seeked", afterSeek);
      element.removeEventListener("canplay", ready);
    };
  }, [source, duration, playing, muted, video, onFailure, onBlocked, onBuffering, trackId, stalled, seekVersion, trimStart, loop]);
  useEffect(() => {
    const element = ref.current;
    return () => { element?.pause(); onBuffering(trackId, false); };
  }, [source, onBuffering, trackId]);
  const props = { ref, src: mediaUrl(source), muted, loop, preload: "auto", onError: () => { onBuffering(trackId, false); onFailure(); }, onWaiting: event => { if (playing && time >= 0 && time < (duration || event.currentTarget.duration || 0) && (video || !muted)) onBuffering(trackId, true); }, onCanPlay: () => onBuffering(trackId, false) };
  return video ? <video {...props} playsInline className="absolute inset-0 h-full w-full object-cover" /> : <audio {...props} />;
}

export function Visual({ segment, size, time, playing, muted, onFailure, onBlocked, opacity = 1, onBuffering, stalled, seekVersion }) {
  const overlayTime = Math.min(time, Math.max(0, segment.duration - 0.000001));
  return <div className="absolute inset-0" style={{ opacity }}>
    {!segment.visual ? <div className="absolute inset-0 bg-black" /> : segment.visual_type === "video" ? <Track source={segment.visual} video time={time} duration={segment.loop_visual ? segment.base_duration : Math.min(segment.visual_duration ?? segment.base_duration, segment.base_duration)} loop={!!segment.loop_visual} playing={playing} muted={muted || !segment.clip_audio} onFailure={onFailure} onBlocked={onBlocked} onBuffering={onBuffering} stalled={stalled} seekVersion={seekVersion} />
      : <img style={imageMotion(segment, time)} src={mediaUrl(segment.visual)} alt={segment.label} onError={onFailure} className="absolute inset-0 h-full w-full object-cover" />}
    <PhotoAnimationLayer plan={segment.photo_animation} time={overlayTime} duration={segment.base_duration} fps={segment.fps} />
    <OverlayLayer frameSize={size} overlays={segment.overlays} logo={segment.overlay_logo} time={overlayTime} duration={segment.duration} animationPreset={segment.photo_animation?.preset} />
  </div>;
}

export function VideoPreviewModal({ open, onClose, video, disabled = false }) {
  if (!open || !video) return null;
  return <EditorDialog open={open} onClose={onClose} title="Preview video" description={`${video.title} · Watch your saved edits before rendering.`} icon={HiOutlinePlay} maxWidth="max-w-4xl" closeLabel="Close preview" footer={<div className="flex justify-end"><button type="button" onClick={onClose} className={editorSecondaryButton}>Close preview</button></div>}>
    <VideoPreview video={video} disabled={disabled} />
  </EditorDialog>;
}

export function VideoPreview({ video, disabled = false, selectedSceneId, compact = false, sceneOnly = false, cutSections, renderCutControls }) {
  const [preview, setPreview] = useState(null);
  const manifest = preview?.videoId === video?.id ? preview.manifest : null;
  const previewSegment = sceneOnly ? manifest?.segments.find(item => String(item.id) === String(selectedSceneId)) : null;
  const playbackSections = useMemo(() => previewSections(manifest, previewSegment, sceneOnly ? cutSections : undefined), [manifest, previewSegment, sceneOnly, cutSections]);
  const playbackStart = playbackSections[0]?.start || 0;
  const playbackEnd = playbackSections[playbackSections.length - 1]?.end || 0;
  const playbackDuration = sectionsDuration(playbackSections);
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
  const previewSelection = useRef({ manifest: null, id: null });
  const timeline = useRef(null);
  const currentVideoId = useRef(video?.id);
  const allowed = ["READY", "COMPLETED", "FAILED"].includes(video?.status);
  // Polling returns new objects even when nothing changed; only an edited timeline reloads.
  const revision = useMemo(() => JSON.stringify([video?.id, video?.status, video?.settings,
    video?.intro, video?.outro, video?.avatar, video?.music,
    video?.scenes?.map(s => [s.id, s.text, s.file, s.voiceover, s.audio_settings, s.cuts, s.scene_image, s.timing, s.pause_after, s.transition_after, s.transition_duration, s.motion_style, s.motion_intensity, s.animation_preset, s.animation_accents, s.overlays, s.overlay_logo])]), [video]);
  useEffect(() => {
    setPlaying(false);
    if (currentVideoId.current !== video?.id) {
      currentVideoId.current = video?.id;
      setTime(0);
      timeRef.current = 0;
    }
    if (!allowed || disabled) return;
    let current = true;
    setLoading(true); setError(""); setMediaError(false);
    getVideoPreview(video.id).then(response => {
      if (!current) return;
      if (!response.ok || !response.data?.segments?.length || !(response.data.duration > 0)) setError(response.message || "Preview is unavailable. Check your scene media and try again.");
      else setPreview({ videoId: video.id, manifest: response.data });
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
      const joined = joinedPosition(playbackSections, anchor.current.position) + (now - anchor.current.wall) / 1000;
      const next = sourcePosition(playbackSections, Math.min(playbackDuration, joined));
      const before = playbackSections.findIndex(s => timeRef.current >= s.start && timeRef.current < s.end);
      const after = playbackSections.findIndex(s => next >= s.start && next < s.end);
      if (before !== after && next < playbackEnd) setSeekVersion(version => version + 1);
      timeRef.current = next;
      // Keep the UI responsive without rendering every browser animation frame.
      if (now - lastUpdate >= 1000 / 30 || next >= playbackEnd) {
        setTime(next);
        lastUpdate = now;
      }
      if (next >= playbackEnd) setPlaying(false);
      else frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, manifest, buffering, playbackEnd, playbackSections, playbackDuration]);
  useEffect(() => {
    const pauseHidden = () => { if (document.hidden) setPlaying(false); };
    document.addEventListener("visibilitychange", pauseHidden);
    return () => document.removeEventListener("visibilitychange", pauseHidden);
  }, []);
  const seek = useCallback(position => {
    const next = sourcePosition(playbackSections, joinedPosition(playbackSections, Math.max(playbackStart, Math.min(playbackEnd, position))));
    anchor.current = { position: next, wall: performance.now() };
    timeRef.current = next;
    setTime(next);
    setSeekVersion(version => version + 1);
  }, [playbackStart, playbackEnd, playbackSections]);
  useEffect(() => {
    if (!manifest) return;
    const changed = previewSelection.current.manifest !== manifest || previewSelection.current.id !== selectedSceneId;
    previewSelection.current = { manifest, id: selectedSceneId };
    if (selectedSceneId == null) { setPlaying(false); seek(timeRef.current); return; }
    const segment = manifest.segments.find(item => String(item.id) === String(selectedSceneId));
    if (segment) { setPlaying(false); seek(changed ? segment.start : timeRef.current); }
  }, [selectedSceneId, manifest, seek]);
  const togglePlayback = () => {
    setError("");
    if (time >= playbackEnd) seek(playbackStart);
    setPlaying(value => !value);
  };
  const failMedia = useCallback(() => setMediaError(true), []);
  const blocked = useCallback(() => { setPlaying(false); setError("Your browser paused the media. Press play to try again."); }, []);
  const musicSpeech = useMemo(() => !manifest?.music ? [] : (manifest.audio_tracks || []).flatMap(track =>
    (track.speech || []).map(([a, b]) => [a - (manifest.music?.start || 0), b - (manifest.music?.start || 0)]),
  ), [manifest]);
  const segments = manifest?.segments || [];
  const index = previewSegment ? segments.indexOf(previewSegment) : Math.max(0, segments.findIndex(segment => time < segment.start + segment.duration));
  const active = previewSegment || (time >= (manifest?.duration || Infinity) ? segments[segments.length - 1] : segments[index]);
  const local = active ? Math.min(time - active.start, active.duration) : 0;
  const previous = segments[index - 1];
  const dissolve = active?.dissolve_in > 0 && local < active.dissolve_in && previous;
  let opacity = 1;
  if (active?.fade_in && local < active.fade_in) opacity = local / active.fade_in;
  if (active?.fade_out && local > active.duration - active.fade_out) opacity = Math.min(opacity, (active.duration - local) / active.fade_out);
  const captionTime = previewSegment ? Math.min(time, playbackEnd - 0.000001) : time;
  const cue = manifest?.captions?.find(c => captionTime >= c.start && captionTime < c.end);
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
    {(!allowed || disabled) && <p role="status" className="rounded-xl bg-gray-50 p-4 text-sm text-gray-500 dark:bg-gray-900/40 dark:text-gray-400">{disabled ? "Preview updates once your changes are saved." : "Preview becomes available when scene processing finishes."}</p>}
    {allowed && <>
      {loading && !disabled && <p role="status" className="py-2 text-center text-xs text-gray-500">{manifest ? "Updating preview…" : "Loading preview…"}</p>}
      {error && <div role="alert" className="mb-3 flex flex-wrap items-center gap-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-900/20 dark:text-amber-200"><span>{error}</span><button type="button" onClick={() => setRetry(value => value + 1)} className="font-semibold underline">Reload preview</button></div>}
      {manifest && <>
        <div className="preview-stage mx-auto w-full max-w-2xl overflow-hidden rounded-xl bg-black" style={{ maxWidth: renderCutControls ? `min(100%, calc(26vh * ${manifest.size[0] / manifest.size[1]}))` : manifest.size[0] < manifest.size[1] ? 280 : manifest.size[0] === manifest.size[1] ? 420 : undefined }}>
          <div role="img" aria-label={`${active?.label || "Video"} preview`} className="relative isolate w-full overflow-hidden bg-black" style={{ aspectRatio: `${manifest.size[0]} / ${manifest.size[1]}` }}>
            {active && <Visual key={active.id} segment={active} size={manifest.size} time={local} playing={playing} muted={muted} opacity={time === 0 && !playing ? 1 : Math.max(0, opacity)} onFailure={failMedia} onBlocked={blocked} onBuffering={onBuffering} stalled={buffering} seekVersion={seekVersion} />}
            {dissolve && <Visual key={`hold-${previous.id}`} segment={previous} size={manifest.size} time={previous.duration} playing={false} muted opacity={1 - local / active.dissolve_in} onFailure={failMedia} onBlocked={blocked} onBuffering={onBuffering} stalled={buffering} seekVersion={seekVersion} />}
            {(manifest.audio_tracks || []).filter(track => time >= track.start - 0.5 && time <= track.start + track.duration + 0.1).map(track => <Track key={`voice-${track.id}`} source={track.source} time={time - track.start} trimStart={track.trim_start} duration={track.duration} volume={voiceGain(time - track.start, track)} playing={playing} muted={muted} onFailure={failMedia} onBlocked={blocked} onBuffering={onBuffering} stalled={buffering} seekVersion={seekVersion} />)}
            {manifest.music && <Track key={`music-${manifest.music.source}`} source={manifest.music.source} loop time={time - manifest.music.start} duration={manifest.music.duration} volume={musicGain(time - manifest.music.start, manifest.music.duration, manifest.music.settings, musicSpeech)} playing={playing} muted={muted} onFailure={failMedia} onBlocked={blocked} onBuffering={onBuffering} stalled={buffering} seekVersion={seekVersion} />}
            <CaptionLayer cue={cue} style={manifest.caption_style} size={manifest.size} config={manifest.caption_config} />
          </div>
        </div>
        <fieldset disabled={disabled || loading} className={`preview-transport mt-4 flex items-center gap-2 sm:gap-3 ${renderCutControls ? "cut-transport" : ""}`}>
          <button type="button" aria-label={playing ? "Pause preview" : "Play preview"} onClick={togglePlayback} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white hover:bg-blue-700">{playing ? <FaPause /> : <FaPlay />}</button>
          <button type="button" aria-label="Restart preview" onClick={() => seek(playbackStart)} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"><FaUndo /></button>
          <input aria-label="Preview playhead" type="range" min="0" max={playbackDuration} step="0.01" value={joinedPosition(playbackSections, time)} onChange={event => seek(sourcePosition(playbackSections, Number(event.target.value)))} aria-hidden={renderCutControls ? true : undefined} tabIndex={renderCutControls ? -1 : undefined} className={renderCutControls ? "sr-only" : "min-w-0 flex-1 accent-blue-600"} />
          <span className="shrink-0 text-xs tabular-nums text-gray-500 dark:text-gray-300">{renderCutControls ? cutClock(joinedPosition(playbackSections, time)) : clock(joinedPosition(playbackSections, time))} / {renderCutControls ? cutClock(playbackDuration) : clock(playbackDuration)}</span>
          <button type="button" aria-label={muted ? "Unmute preview" : "Mute preview"} onClick={() => setMuted(value => !value)} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700">{muted ? <FaVolumeMute /> : <FaVolumeUp />}</button>
        </fieldset>
        {renderCutControls?.({ position: joinedPosition(playbackSections, time), onSeek: position => seek(sourcePosition(playbackSections, position)), duration: playbackDuration, onTogglePlayback: togglePlayback, playing, ready: !!previewSegment && !loading && !error })}
        {!compact && <> <h2 className="mt-5 text-sm font-semibold text-gray-900 dark:text-white">Scene timeline</h2>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Choose a scene to jump to it.</p>
        <Timeline segments={segments} activeId={activeId} local={local} activeButton={activeButton} timelineRef={timeline} onSeek={seek} playbackSections={playbackSections} /></>}
        {buffering && <p role="status" className="mt-2 text-xs text-gray-500">Buffering preview…</p>}
        {mediaError && <p role="status" className="mt-2 text-xs text-amber-700 dark:text-amber-300">Some media could not load. Check the scene files or reload the preview.</p>}
        <details className="mt-3 text-xs leading-relaxed text-gray-500 dark:text-gray-400"><summary className="cursor-pointer font-medium">About this preview</summary><p className="mt-2">Preview plays without rendering a video file. Caption timing is estimated; caption appearance may vary in the render.{manifest.render_only?.length > 0 ? ` Render to include ${manifest.render_only.join(", ")}.` : ""}</p></details>
      </>}
    </>}
  </section>;
}

const TimelineItem = memo(function TimelineItem({ segment, active, progress, activeButton, onSeek, playbackDuration = segment.duration }) {
  return <button type="button" ref={active ? activeButton : null} aria-label={`Preview ${segment.label}`} aria-current={active ? "true" : undefined} onClick={() => onSeek(segment.start)} style={{ width: Math.max(100, Math.min(240, playbackDuration * 18)) }} className={`relative shrink-0 overflow-hidden rounded-xl border-2 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 ${active ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20" : "border-gray-200 dark:border-gray-700"}`}>
              <div className="relative h-14 overflow-hidden bg-gray-100 dark:bg-gray-900">{segment.visual && (segment.visual_type === "video" ? <DeferredVideo src={mediaUrl(segment.visual)} muted playsInline preload="metadata" className="h-full w-full object-cover" /> : <img src={mediaUrl(segment.visual)} alt="" loading="lazy" decoding="async" className="h-full w-full object-cover" />)}{!segment.visual && <span className="flex h-full items-center justify-center text-xs text-gray-400">No visual</span>}</div>
              <div className="px-2 py-1.5"><span className="block text-xs font-semibold text-gray-700 dark:text-gray-200">{segment.label}</span><span className="block text-[11px] text-gray-500 dark:text-gray-400">{playbackDuration.toFixed(1)}s{segment.pause > 0 ? ` · +${segment.pause}s pause` : ""}</span></div>
              {active && <span aria-hidden="true" className="pointer-events-none absolute bottom-0 top-0 w-0.5 bg-blue-500" style={{ left: `${Math.min(100, Math.max(0, progress / playbackDuration * 100))}%` }} />}
            </button>;
});

function Timeline({ segments, activeId, local, activeButton, timelineRef, onSeek, playbackSections }) {
  return <nav ref={timelineRef} aria-label="Preview timeline" className="mt-3 flex gap-2 overflow-x-auto pb-2">
          {segments.map((segment, segmentIndex) => <React.Fragment key={segment.id}>
            <TimelineItem segment={segment} active={segment.id === activeId} playbackDuration={sectionsDuration(previewSections({ playback_sections: playbackSections }, segment))} progress={segment.id === activeId ? joinedPosition(previewSections({ playback_sections: playbackSections }, segment).map(s => ({ start: s.start - segment.start, end: s.end - segment.start })), local) : 0} activeButton={activeButton} onSeek={onSeek} />
            {segmentIndex < segments.length - 1 && <span className="flex shrink-0 items-center text-[10px] text-gray-400">{segment.kind === "scene" && segments[segmentIndex + 1].kind === "scene" ? ({ CUT: "Cut", FADE: "Fade", DISSOLVE: "Dissolve" }[segment.transition]) : "Cut"}</span>}
          </React.Fragment>)}
        </nav>;
}
