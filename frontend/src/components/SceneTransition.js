export const transitionDurations = [0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, 3];
export const transitionStyles = [["CUT", "Cut"], ["FADE", "Fade through black"], ["DISSOLVE", "Cross dissolve"]];
const inputClass = "rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 disabled:opacity-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200";

export function SceneTransition({ scene, nextNumber, disabled, saving, onChange, settings = {} }) {
  const selected = scene.transition_after || "DEFAULT";
  const effective = selected === "DEFAULT" ? settings.transition_default || "FADE" : selected;
  const duration = scene.transition_duration ?? "";
  const inheritedDuration = settings.transition_duration ? `${settings.transition_duration}s` : "Automatic";
  return <fieldset disabled={disabled} className="mb-5 flex min-w-0 flex-wrap items-center justify-center gap-3 rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 dark:border-gray-700 dark:bg-gray-900/30">
    <legend className="sr-only">Transition to scene {nextNumber}</legend>
    <span className="text-xs text-gray-500 dark:text-gray-400">{saving ? "Saving transition…" : `To scene ${nextNumber}`}</span>
    <label className="flex items-center gap-2 text-xs text-gray-500">Style<select aria-label="Transition style" className={inputClass} value={selected} onChange={event => onChange(scene, { transition_after: event.target.value, transition_duration: scene.transition_duration ?? null })}>
      <option value="DEFAULT">Video default ({transitionStyles.find(([value]) => value === (settings.transition_default || "FADE"))?.[1]})</option>
      {transitionStyles.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
    </select></label>
    <label className="flex items-center gap-2 text-xs text-gray-500">Duration<select aria-label="Transition duration" disabled={disabled || effective === "CUT"} className={inputClass} value={duration} onChange={event => onChange(scene, { transition_after: selected, transition_duration: event.target.value ? Number(event.target.value) : null })}>
      <option value="">Video default ({inheritedDuration})</option>
      {transitionDurations.map(value => <option key={value} value={value}>{value}s</option>)}
    </select></label>
    <span className="text-xs text-gray-400">{effective === "CUT" ? "Switch instantly" : effective === "DISSOLVE" ? "Blend into the next scene" : "Fade through black"}</span>
  </fieldset>;
}
