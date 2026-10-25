import React, { useId } from "react";
import { editorInput } from "./ui/EditorDialog";

export function VisualContinuity({ value, onChange, disabled = false, description = "Describe recurring characters, clothing, important props, locations, and visual style. These details accompany every AI visual request." }) {
  const id = useId();
  return <section className="space-y-2">
    <label htmlFor={id} className="block text-sm font-semibold">Character &amp; setting continuity</label>
    <p id={id + "-help"} className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">{description}</p>
    <textarea id={id} aria-describedby={id + "-help"} rows={5} maxLength={3000} value={value} disabled={disabled} onChange={event => onChange(event.target.value)} className={editorInput} placeholder="Milo: a small orange fox with a white muzzle, green scarf, and brown satchel. World: a watercolor forest with warm evening light. Keep these details whenever Milo appears." />
    <p className="text-xs text-gray-500 dark:text-gray-400">Optional. Applies to future AI generations; existing visuals stay as they are. Improves consistency but does not guarantee identical characters.</p>
  </section>;
}
