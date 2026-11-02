import { photoPresets } from "../utils/photoAnimation";

const controlClass = "mt-2 w-full rounded-lg border border-gray-300 bg-white p-2 text-sm dark:border-gray-600 dark:bg-gray-900";
const timingFields = [["start_fraction", "Show at (%)"], ["end_fraction", "Hide at (%)"]];
const positions = [["top-left", "Top left"], ["top-center", "Top center"], ["top-right", "Top right"], ["middle-center", "Center"]];

export function VisualEditingFields({ editing, onChange, disabled, photoAnimations = true }) {
  const overlays = editing.overlays || [];
  const nextStart = overlays.at(-1)?.end_fraction ?? 0;
  const canAddLabel = overlays.length < 2 && nextStart < 1;
  const change = (field, value) => onChange({ ...editing, [field]: value });
  const changeLabel = (index, field, value) => change("overlays", overlays.map((item, i) => i === index ? { ...item, [field]: value } : item));
  const addLabel = () => change("overlays", [...overlays, {
    text: "", position: "top-center", start_fraction: nextStart,
    end_fraction: overlays.length ? 1 : .5,
  }]);
  return <fieldset disabled={disabled} className="rounded-xl border border-blue-100 bg-blue-50/40 p-3 dark:border-gray-600 dark:bg-gray-900/40">
    <legend className="px-1 text-sm font-semibold">Visual emphasis</legend>
    {photoAnimations && <label className="block text-sm font-medium">Photo animation
      <select value={editing.animation_preset || "NONE"} onChange={event => change("animation_preset", event.target.value)} className={controlClass}>
        {photoPresets.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select>
    </label>}
    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{photoAnimations ? "Photo animations reuse your images. " : "Camera movement comes from your video clips. "}Transition: {editing.transition_after?.toLowerCase()} · Pause: {editing.pause_after}s. You can adjust these in the scene editor.</p>
    <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">Labels emphasize a question, number, or reveal. Timing is a percentage of the finished scene and is approximate, not word-synchronized. Keep labels short and show one at a time.</p>
    {overlays.map((item, index) => <div key={index} className="mt-3 rounded-lg border border-gray-200 p-3 dark:border-gray-600">
      <label className="block text-sm font-medium">Label {index + 1}
        <input required maxLength={80} value={item.text} onChange={event => changeLabel(index, "text", event.target.value)} className={controlClass} />
      </label>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <label className="block text-sm">Position
          <select value={item.position || "top-center"} onChange={event => changeLabel(index, "position", event.target.value)} className={controlClass}>
            {positions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        {timingFields.map(([field, label]) => <label key={field} className="block text-sm">{label}
          <input required type="number" min={0} max={100} step={1} value={Math.round(item[field] * 100)} onChange={event => changeLabel(index, field, Number(event.target.value) / 100)} className={controlClass} />
        </label>)}
      </div>
      <button type="button" onClick={() => change("overlays", overlays.filter((_, i) => i !== index))} className="mt-3 text-xs font-medium text-red-600 dark:text-red-400">Remove label {index + 1}</button>
    </div>)}
    <button type="button" disabled={disabled || !canAddLabel} onClick={addLabel} className="mt-3 rounded-lg border border-gray-300 px-3 py-2 text-xs font-medium disabled:opacity-40 dark:border-gray-600">Add label</button>
  </fieldset>;
}
