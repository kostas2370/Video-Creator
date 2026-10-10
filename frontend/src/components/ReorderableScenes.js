import { useEffect, useRef, useState } from "react";
import { RiDraggable } from "react-icons/ri";
import { SceneTransition } from "./SceneTransition";
import { Scene } from "./Scene";

export function ReorderableScenes({ scenes, disabled, saving, onReorder, setUpdated, videoFormat, onTransition, pendingTransition, transitionSettings }) {
  const [drag, setDrag] = useState(null);
  const dragRef = useRef(null);
  const listRef = useRef(null);
  const dragging = drag !== null;

  const updateDrag = event => {
    const current = dragRef.current;
    if (!current) return;
    const rows = Array.from(listRef.current.querySelectorAll("[data-scene-order]"));
    const target = rows.findIndex(row => {
      const rect = row.getBoundingClientRect();
      return event.clientY < rect.top + rect.height / 2;
    });
    const next = { ...current, x: event.clientX, y: event.clientY, target: target < 0 ? scenes.length : target };
    dragRef.current = next;
    setDrag(next);
  };
  const move = (from, to) => {
    if (disabled || from === to) return;
    const ordered = [...scenes];
    const [scene] = ordered.splice(from, 1);
    ordered.splice(to, 0, scene);
    onReorder(ordered);
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
      if (current) {
        if (current.y < 80) window.scrollBy(0, -12);
        else if (current.y > window.innerHeight - 80) window.scrollBy(0, 12);
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

  return <div ref={listRef}>
    {scenes.length > 1 && <p id="scene-reorder-help" role="status" className="mb-4 text-xs text-gray-500 dark:text-gray-400">{saving ? "Saving scene order…" : "Drag the handle to reorder scenes. You can also focus it and use the up and down arrow keys."}</p>}
    {scenes.map((scene, index) => <div key={scene.id} data-scene-order={index} className="relative mb-5">
      {drag?.target === index && drag.target !== drag.from && drag.target !== drag.from + 1 && <div className="pointer-events-none absolute -top-3 left-0 right-0 h-1 rounded-full bg-blue-500" />}
      <div className={drag?.from === index ? "opacity-40" : ""}>
        <Scene scene={scene} index={index} setUpdated={setUpdated} video_format={videoFormat} reorderHandle={scenes.length > 1 && <button type="button" disabled={disabled} aria-label={`Move scene ${index + 1}`} aria-describedby="scene-reorder-help" className="touch-none rounded-lg p-2 text-gray-400 cursor-grab hover:bg-blue-50 hover:text-blue-600 active:cursor-grabbing focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-default disabled:opacity-30 dark:hover:bg-gray-700" onPointerDown={event => {
          if (disabled || event.button !== 0) return;
          event.preventDefault();
          event.currentTarget.focus();
          event.currentTarget.setPointerCapture(event.pointerId);
          dragRef.current = { from: index, target: index, x: event.clientX, y: event.clientY };
          updateDrag(event);
        }} onPointerMove={event => { if (dragRef.current) updateDrag(event); }} onPointerUp={finishDrag} onPointerCancel={finishDrag} onLostPointerCapture={finishDrag} onKeyDown={event => {
          if (event.key === "Escape" && dragRef.current) { event.preventDefault(); dragRef.current = null; setDrag(null); }
          if (event.key === "ArrowUp" || event.key === "ArrowDown") {
            event.preventDefault();
            move(index, Math.max(0, Math.min(scenes.length - 1, index + (event.key === "ArrowUp" ? -1 : 1))));
          }
        }}><RiDraggable className="h-5 w-5" /></button>} />
      </div>
      {index < scenes.length - 1 && <div className="mt-5"><SceneTransition scene={scene} nextNumber={index + 2} disabled={disabled} saving={pendingTransition === scene.id} onChange={onTransition} settings={transitionSettings} /></div>}
    </div>)}
    {drag?.target === scenes.length && drag.from !== scenes.length - 1 && <div className="-mt-3 mb-5 h-1 rounded-full bg-blue-500" />}
    {drag && <div aria-hidden="true" style={{ left: Math.min(drag.x + 12, window.innerWidth - 160), top: drag.y + 12 }} className="pointer-events-none fixed z-[80] max-w-[150px] rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-xl">Moving scene {drag.from + 1}</div>}
  </div>;
}
