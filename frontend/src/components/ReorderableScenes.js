import { useEffect, useRef, useState } from "react";
import { RiDraggable } from "react-icons/ri";
import { HiOutlineChevronLeft, HiOutlineChevronRight, HiOutlineFilm } from "react-icons/hi2";
import { SceneTransition } from "./SceneTransition";
import { Scene } from "./Scene";
import { API_HOST } from "../endpoints";
import { isVideo } from "../utils/media";
import { formatDuration } from "../utils/timing";

export function reorderScene(scenes, from, to) {
  const ordered = [...scenes];
  const [scene] = ordered.splice(from, 1);
  ordered.splice(to, 0, scene);
  return ordered;
}

export function ReorderableScenes({ manual, scenes, actions, selectedSceneId, onSelectScene, disabled, saving, onReorder, setUpdated, videoFormat, onTransition, pendingTransition, transitionSettings, onTiming, pendingTiming, onMotion, pendingMotion }) {
  const [drag, setDrag] = useState(null);
  const dragRef = useRef(null);
  const listRef = useRef(null);
  const dragging = drag !== null;
  const activeId = selectedSceneId ?? scenes[0]?.id;
  const selectedIndex = Math.max(0, scenes.findIndex(scene => scene.id === activeId));
  const selected = scenes[selectedIndex];

  const updateDrag = event => {
    const current = dragRef.current;
    if (!current) return;
    const cards = Array.from(listRef.current.querySelectorAll("[data-scene-order]"));
    const target = cards.findIndex(card => {
      const rect = card.getBoundingClientRect();
      return event.clientX < rect.left + rect.width / 2;
    });
    const next = { ...current, x: event.clientX, y: event.clientY, target: target < 0 ? scenes.length : target };
    dragRef.current = next;
    setDrag(next);
  };
  const move = (from, to) => {
    if (disabled || from === to) return;
    onReorder(reorderScene(scenes, from, to));
  };
  const finishDrag = event => {
    if (!dragRef.current) return;
    if (event.type === "pointerup") updateDrag(event);
    const current = dragRef.current;
    const bounds = listRef.current.getBoundingClientRect();
    dragRef.current = null;
    setDrag(null);
    if (event.type === "pointerup" && event.clientX >= bounds.left && event.clientX <= bounds.right && event.clientY >= bounds.top && event.clientY <= bounds.bottom) {
      move(current.from, current.target > current.from ? current.target - 1 : current.target);
    }
  };

  useEffect(() => {
    if (!dragging) return;
    let frame;
    const scroll = () => {
      const current = dragRef.current;
      const list = listRef.current;
      if (current && list) {
        const bounds = list.getBoundingClientRect();
        if (current.x < bounds.left + 48) list.scrollLeft -= 10;
        else if (current.x > bounds.right - 48) list.scrollLeft += 10;
        updateDrag({ clientX: current.x, clientY: current.y });
      }
      frame = requestAnimationFrame(scroll);
    };
    frame = requestAnimationFrame(scroll);
    return () => cancelAnimationFrame(frame);
  }, [dragging]);
  useEffect(() => {
    dragRef.current = null;
    setDrag(null);
  }, [scenes, disabled]);
  useEffect(() => {
    const list = listRef.current;
    const card = list?.querySelector('[aria-pressed="true"]')?.closest("[data-scene-order]");
    if (!card) return;
    const bounds = list.getBoundingClientRect();
    const rect = card.getBoundingClientRect();
    if (rect.left < bounds.left) list.scrollLeft += rect.left - bounds.left - 8;
    else if (rect.right > bounds.right) list.scrollLeft += rect.right - bounds.right + 8;
  }, [activeId, scenes]);

  return <div className="min-w-0 space-y-5">
    {scenes.length > 0 && <section aria-label="Horizontal storyboard" className="editor-strip min-w-0 rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="mb-2 flex items-center justify-between gap-3"><h2 className="text-sm font-semibold">Scenes <span className="ml-1 font-normal text-gray-500 dark:text-gray-400">{scenes.length}</span></h2><div className="flex items-center gap-2">{actions}<div className="flex gap-1">{[["left", HiOutlineChevronLeft, -1], ["right", HiOutlineChevronRight, 1]].map(([direction, Icon, sign]) => <button key={direction} type="button" aria-label={`Scroll storyboard ${direction}`} onClick={() => listRef.current?.scrollBy({ left: sign * listRef.current.clientWidth * 0.8, behavior: "smooth" })} className="rounded-lg border border-gray-200 p-2 text-gray-500 hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"><Icon aria-hidden="true" className="h-4 w-4" /></button>)}</div></div></div>
      <p id="scene-reorder-help" role="status" className="mb-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">{saving ? "Saving scene order…" : "Select a scene to edit. Drag the handle to reorder."}<span className="sr-only"> Focus a handle and use the left and right arrow keys to reorder.</span></p>
      <div ref={listRef} aria-label="Scene order" className="flex gap-3 overflow-x-auto overscroll-x-contain px-1 pb-3 pt-1">
        {scenes.map((scene, index) => {
          const file = scene.scene_image?.file;
          const insertion = drag?.target === index && drag.target !== drag.from && drag.target !== drag.from + 1;
          return <div key={scene.id} data-scene-order={index} className={`editor-card ${activeId === scene.id ? "editor-card-selected" : ""} relative w-40 shrink-0 rounded-xl border p-2 ${activeId === scene.id ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20" : "border-gray-200 dark:border-gray-600"} ${drag?.from === index ? "opacity-40" : ""}`}>
            {insertion && <span aria-hidden="true" className="pointer-events-none absolute -left-2 bottom-0 top-0 w-1 rounded-full bg-blue-500" />}
            <button type="button" aria-label={`Edit scene ${index + 1}`} aria-pressed={activeId === scene.id} onClick={() => onSelectScene?.(scene.id)} className="block w-full rounded-lg text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">
              <span className="relative mb-2 flex aspect-video items-center justify-center overflow-hidden rounded-lg bg-gray-100 dark:bg-gray-900">
                {file ? isVideo(file) ? <video src={API_HOST + file} muted playsInline preload="metadata" aria-hidden="true" className="pointer-events-none h-full w-full object-cover" /> : <img src={API_HOST + file} alt="" loading="lazy" draggable={false} className="h-full w-full object-cover" /> : <HiOutlineFilm aria-hidden="true" className="h-7 w-7 text-gray-400" />}
                <span className="absolute bottom-1 right-1 rounded bg-black/70 px-1.5 py-0.5 text-[10px] text-white">{formatDuration(scene.timing?.duration)}</span>
              </span>
              <span className="block text-xs font-semibold">Scene {index + 1}</span><span className="mt-1 block truncate text-xs text-gray-500 dark:text-gray-400">{scene.text || "Add text or media"}</span>
            </button>
            {scenes.length > 1 && <button type="button" disabled={disabled} aria-label={`Move scene ${index + 1}`} aria-describedby="scene-reorder-help" className="mt-2 flex min-h-9 w-full touch-none items-center justify-center rounded-lg bg-gray-100 py-1.5 text-gray-500 cursor-grab hover:bg-blue-100 hover:text-blue-600 active:cursor-grabbing focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-default disabled:opacity-30 dark:bg-gray-700 dark:text-gray-300" onPointerDown={event => {
              if (disabled || event.button !== 0) return;
              event.preventDefault();
              event.currentTarget.focus();
              event.currentTarget.setPointerCapture(event.pointerId);
              dragRef.current = { from: index, target: index, x: event.clientX, y: event.clientY };
              updateDrag(event);
            }} onPointerMove={event => { if (dragRef.current) updateDrag(event); }} onPointerUp={finishDrag} onPointerCancel={finishDrag} onLostPointerCapture={finishDrag} onKeyDown={event => {
              if (event.key === "Escape" && dragRef.current) { event.preventDefault(); dragRef.current = null; setDrag(null); }
              if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
                event.preventDefault();
                move(index, Math.max(0, Math.min(scenes.length - 1, index + (event.key === "ArrowLeft" ? -1 : 1))));
              }
            }}><RiDraggable aria-hidden="true" className="h-4 w-4" /></button>}
          </div>;
        })}
        {drag?.target === scenes.length && drag.from !== scenes.length - 1 && <span aria-hidden="true" className="w-1 shrink-0 rounded-full bg-blue-500" />}
      </div>
    </section>}
    {selected && <div>
      <Scene key={selected.id} manual={manual} scene={selected} index={selectedIndex} nextScene={scenes[selectedIndex + 1]} onTiming={onTiming} timingDisabled={disabled} timingSaving={pendingTiming === selected.id} onMotion={onMotion} motionDisabled={disabled} motionSaving={pendingMotion === selected.id} setUpdated={setUpdated} video_format={videoFormat} transitionControl={selectedIndex < scenes.length - 1 ? <SceneTransition scene={selected} nextNumber={selectedIndex + 2} disabled={disabled} saving={pendingTransition === selected.id} onChange={onTransition} settings={transitionSettings} /> : null} />
    </div>}
    {drag && <div aria-hidden="true" style={{ left: Math.min(drag.x + 12, window.innerWidth - 160), top: drag.y + 12 }} className="pointer-events-none fixed z-[80] max-w-[150px] rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-xl">Moving scene {drag.from + 1}</div>}
  </div>;
}
