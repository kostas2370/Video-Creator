import { useEffect, useRef } from "react";

export function CreationSteps({ steps, current, onSelect, disabled = false }) {
  const navigation = useRef(null);
  const previous = useRef(current);
  useEffect(() => {
    if (previous.current === current) return;
    previous.current = current;
    navigation.current?.scrollIntoView?.({ block: "start" });
    navigation.current?.querySelector('[aria-current="step"]')?.focus({ preventScroll: true });
  }, [current]);
  return <nav ref={navigation} aria-label="Creation steps" className="mb-8 flex scroll-mt-6 gap-2 rounded-2xl bg-gray-100/80 p-1.5 dark:bg-gray-900/60">{steps.map((label, index) => <button key={label} type="button" disabled={disabled} onClick={() => onSelect(index)} aria-current={current === index ? "step" : undefined} className={`flex min-w-0 flex-1 items-center justify-center gap-2 rounded-xl px-2 py-3 text-xs font-semibold transition sm:text-sm ${current === index ? "bg-white text-indigo-700 shadow-sm dark:bg-gray-800 dark:text-indigo-100" : "text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"}`}><span aria-hidden="true" className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs ${current === index ? "bg-indigo-100 dark:bg-indigo-900" : "bg-gray-200/70 dark:bg-gray-800"}`}>{index < current ? "✓" : index + 1}</span><span className="truncate">{label}</span></button>)}</nav>;
}
