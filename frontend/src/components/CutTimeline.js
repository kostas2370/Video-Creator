import React, { useEffect, useRef, useState } from "react";
import { HiOutlineArrowUturnLeft, HiOutlineArrowUturnRight, HiOutlineScissors, HiOutlineTrash, HiOutlineMinus, HiOutlinePlus, HiOutlineLink, HiOutlineFilm } from "react-icons/hi2";
import { API_HOST } from "../endpoints";
import { isVideo } from "../utils/media";
import { sectionsDuration, cutClock, sourcePosition, joinedPosition } from "../utils/cuts";

export { cutClock } from "../utils/cuts";

// Decode a small filmstrip locally. Missing or cross-origin media keeps a usable timeline.
function useFilmstrip(scene, duration) {
  const source = scene.scene_image?.file;
  const url = source ? (/^https?:\/\//i.test(source) ? source : `${API_HOST}${source}`) : null;
  const [strip, setStrip] = useState({ source: null, frames: [] });
  useEffect(() => {
    if (!url || !isVideo(url)) return;
    let cancelled = false;
    const video = document.createElement("video");
    video.muted = true;
    video.playsInline = true;
    video.crossOrigin = "anonymous";
    video.preload = "auto";
    let rejectPending;
    let timer;
    const wait = event => new Promise((resolve, reject) => {
      const cleanup = () => { clearTimeout(timer); video.removeEventListener(event, done); video.removeEventListener("error", fail); rejectPending = null; };
      const done = () => { cleanup(); resolve(); };
      const fail = () => { cleanup(); reject(new Error("Filmstrip unavailable")); };
      rejectPending = fail;
      video.addEventListener(event, done, { once: true });
      video.addEventListener("error", fail, { once: true });
      timer = setTimeout(fail, 5000);
    });
    const load = async () => {
      const metadata = wait("loadedmetadata");
      video.src = url;
      await metadata;
      const canvas = document.createElement("canvas");
      canvas.width = 160;
      canvas.height = 90;
      const context = canvas.getContext("2d");
      if (!context) return;
      const frames = [];
      let lastTime = -1;
      for (let index = 0; index < 12 && !cancelled; index++) {
        const time = Math.min(Math.max(0, video.duration - 0.05), duration * (index + 0.5) / 12);
        if (Math.abs(time - lastTime) < 0.001 && frames.length) { frames.push(frames[frames.length - 1]); continue; }
        const seeked = wait("seeked");
        video.currentTime = Math.max(0.001, time);
        await seeked;
        lastTime = time;
        if (cancelled) return;
        const scale = Math.max(160 / video.videoWidth, 90 / video.videoHeight);
        context.drawImage(video, (160 - video.videoWidth * scale) / 2, (90 - video.videoHeight * scale) / 2, video.videoWidth * scale, video.videoHeight * scale);
        frames.push(canvas.toDataURL("image/jpeg", 0.65));
      }
      if (!cancelled) setStrip({ source: url, frames });
    };
    load().catch(() => {});
    return () => { cancelled = true; rejectPending?.(); video.removeAttribute("src"); video.load(); };
  }, [url, duration]);
  if (url && !isVideo(url)) return [url];
  return strip.source === url ? strip.frames : [];
}

export function CutTimeline({ scene, fullVideo = false, sourceScenes = [], sourceSections = [], sections, sourceDuration, position, selected, onSelect, onSeek, onSplit, onRemove, onUndo, onRedo, onReset, canSplit, canUndo, canRedo, disabled }) {
  const [zoom, setZoom] = useState(1);
  const track = useRef(null);
  const playhead = useRef(null);
  const drag = useRef(null);
  useEffect(() => { if (!disabled) playhead.current?.focus({ preventScroll: true }); }, [disabled]);
  const frames = useFilmstrip(scene, sourceDuration);
  const duration = sectionsDuration(sections);
  const section = sections[selected] || sections[0];
  const removed = Math.max(0, sourceDuration - duration);
  const source = section ? `${cutClock(section.start)} → ${cutClock(section.end)}` : "";
  const ticks = Array.from({ length: 6 * zoom + 1 }, (_, index) => duration * index / (6 * zoom));
  const scrub = event => {
    if (!track.current || disabled) return;
    const bounds = track.current.getBoundingClientRect();
    if (!bounds.width) return;
    const next = Math.max(0, Math.min(duration, (event.clientX - bounds.left) / bounds.width * duration));
    onSeek(next);
  };
  const finishDrag = event => {
    if (drag.current !== event.pointerId) return;
    drag.current = null;
    if (track.current?.hasPointerCapture?.(event.pointerId)) track.current.releasePointerCapture(event.pointerId);
  };
  return <fieldset disabled={disabled} className="cut-timeline mt-5 min-w-0 overflow-hidden rounded-2xl border">
    <div className="cut-timeline-toolbar flex flex-wrap items-center justify-between gap-3 px-3 py-2.5 sm:px-4">
      <div className="flex items-center gap-1">
        <button type="button" disabled={!canSplit} aria-label="Split at playhead" title="Split at playhead (S)" onClick={onSplit} className="cut-tool cut-tool-primary"><HiOutlineScissors aria-hidden="true" /><span>Split</span><kbd>S</kbd></button>
        <button type="button" disabled={sections.length < 2} aria-label="Remove selected section" title="Remove selected section (Delete)" onClick={onRemove} className="cut-tool cut-tool-delete"><HiOutlineTrash aria-hidden="true" /><span>Delete</span><kbd>⌫</kbd></button>
        <span className="cut-tool-divider" />
        <button type="button" disabled={!canUndo} aria-label="Undo cut" title="Undo cut (⌘/Ctrl Z)" onClick={onUndo} className="cut-tool cut-tool-icon"><HiOutlineArrowUturnLeft aria-hidden="true" /></button>
        <button type="button" disabled={!canRedo} aria-label="Redo cut" title="Redo cut (⌘/Ctrl Shift Z)" onClick={onRedo} className="cut-tool cut-tool-icon"><HiOutlineArrowUturnRight aria-hidden="true" /></button>
      </div>
      <div className="flex items-center gap-1">
        <button type="button" aria-label="Zoom out timeline" disabled={zoom === 1} onClick={() => setZoom(current => Math.max(1, current - 1))} className="cut-tool cut-tool-icon"><HiOutlineMinus aria-hidden="true" /></button>
        <span className="cut-zoom-value" aria-live="polite">{zoom === 1 ? "Fit" : `${zoom}×`}</span>
        <button type="button" aria-label="Zoom in timeline" disabled={zoom === 6} onClick={() => setZoom(current => Math.min(6, current + 1))} className="cut-tool cut-tool-icon"><HiOutlinePlus aria-hidden="true" /></button>
      </div>
    </div>
    <div className="cut-track-scroll overflow-x-auto overscroll-x-contain px-4 pb-4 pt-2">
      <div ref={track} className="cut-track relative touch-none select-none" style={{ width: `${zoom * 100}%` }} onPointerDown={event => {
        if (disabled || event.button !== 0) return;
        event.preventDefault();
        const index = event.target.closest?.("[data-cut-section]")?.getAttribute("data-cut-section");
        if (index !== undefined && index !== null) onSelect(Number(index));
        playhead.current?.focus({ preventScroll: true });
        drag.current = event.pointerId;
        track.current.setPointerCapture?.(event.pointerId);
        scrub(event);
      }} onPointerMove={event => { if (drag.current === event.pointerId) scrub(event); }} onPointerUp={finishDrag} onPointerCancel={finishDrag} onLostPointerCapture={event => { if (drag.current === event.pointerId) drag.current = null; }}>
        <div aria-hidden="true" className="cut-ruler relative h-8">{ticks.map((time, index) => <span key={index} className={`cut-ruler-tick ${index === ticks.length - 1 ? "cut-ruler-last" : ""}`} style={{ left: `${time / duration * 100}%` }}>{cutClock(time)}</span>)}</div>
        <div aria-label={fullVideo ? "Video cut sections" : "Scene cut sections"} className="cut-filmstrip flex h-16">{sections.map((item, index) => {
          const length = item.end - item.start;
          const offset = sectionsDuration(sections.slice(0, index));
          const cells = Math.max(1, Math.ceil(length / duration * 12 * zoom));
          return <button type="button" key={index} data-cut-section={index} aria-label={`Section ${index + 1}, source ${cutClock(item.start)} to ${cutClock(item.end)}`} aria-pressed={selected === index} title={`Section ${index + 1} · ${length.toFixed(2)}s · source ${sourceDuration ? cutClock(item.start) : ""}–${cutClock(item.end)}`} className="cut-section relative min-w-0 shrink-0 overflow-hidden text-left" style={{ width: `${length / duration * 100}%` }} onClick={event => { if (!event.detail) { onSelect(index); onSeek(offset); } }}>
            <div aria-hidden="true" className="cut-section-frames absolute inset-0 flex">{fullVideo ? Array.from({ length: cells }, (_, frame) => {
              const raw = sourcePosition(sourceSections, item.start + length * (frame + 0.5) / cells);
              const segment = sourceScenes.find(s => raw >= s.start && raw < s.start + s.duration);
              const url = segment?.visual;
              return url && !isVideo(url) ? <img key={frame} src={/^https?:\/\//i.test(url) ? url : `${API_HOST}${url}`} alt="" draggable={false} className="h-full min-w-0 flex-1 object-cover" /> : <span key={frame} className="cut-section-placeholder"><HiOutlineFilm /></span>;
            }) : frames.length ? Array.from({ length: cells }, (_, frame) => {
              const sourceTime = item.start + length * (frame + 0.5) / cells;
              const image = frames[Math.min(frames.length - 1, Math.floor(sourceTime / sourceDuration * frames.length))];
              return <img key={frame} src={image} alt="" draggable={false} className="h-full min-w-0 flex-1 object-cover" />;
            }) : <span className="cut-section-placeholder"><HiOutlineFilm /></span>}</div>
            <span aria-hidden="true" className="cut-section-shade absolute inset-0" />
            <span className="cut-section-label absolute inset-x-0 bottom-0 flex items-end justify-between gap-2 overflow-hidden px-2.5 py-2"><span className="truncate text-xs font-semibold">Section {index + 1}</span><span className="shrink-0 text-[10px] tabular-nums">{length.toFixed(2)}s</span></span>
          </button>;
        })}</div>
        {fullVideo && <div aria-label="Scenes in cut" className="mt-2 flex flex-wrap gap-1">{sourceScenes.filter(segment => sections.some(section => {
          const start = joinedPosition(sourceSections, segment.start);
          const end = joinedPosition(sourceSections, segment.start + segment.duration);
          return section.end > start && section.start < end;
        })).map(segment => <span key={segment.id} className="rounded bg-blue-500/10 px-2 py-1 text-[10px]">{segment.label}</span>)}</div>}
        <div className="cut-linked-track mt-2 flex h-6 items-center gap-2 overflow-hidden rounded-md px-2 text-[10px] font-medium"><HiOutlineLink aria-hidden="true" className="h-3 w-3 shrink-0" /><span className="truncate">Audio, captions &amp; overlays linked</span></div>
        <div ref={playhead} role="slider" tabIndex={disabled ? -1 : 0} aria-label="Cut timeline playhead" aria-valuemin={0} aria-valuemax={duration} aria-valuenow={Math.min(duration, Math.max(0, position))} aria-valuetext={`${cutClock(position)} of ${cutClock(duration)}`} aria-disabled={disabled} className="cut-playhead absolute bottom-0 top-0" style={{ left: `${Math.max(0, Math.min(100, position / duration * 100))}%` }}><span className="cut-playhead-cap" /></div>
      </div>
    </div>
    <div className="cut-timeline-footer flex flex-wrap items-center justify-between gap-3 px-4 py-3">
      <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 text-xs"><span className="cut-selection-label font-semibold">Section {selected + 1}</span><span className="cut-source-time font-mono tabular-nums">{source}</span><span className="cut-source-caption">{fullVideo ? "in video after scene cuts" : "in original scene"}</span></div>
      <button type="button" disabled={!removed && sections.length === 1} onClick={onReset} className="cut-reset">{fullVideo ? "Restore full video" : "Restore full scene"}</button>
    </div>
  </fieldset>;
}
