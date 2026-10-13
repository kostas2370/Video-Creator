const styles = [["NONE", "No motion"], ["AUTO", "Auto"], ["ZOOM_IN", "Zoom in"], ["ZOOM_OUT", "Zoom out"], ["PAN_LEFT", "Pan left"], ["PAN_RIGHT", "Pan right"], ["PAN_UP", "Pan up"], ["PAN_DOWN", "Pan down"]];
const inputClass = "rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm text-gray-700 focus:ring-2 focus:ring-blue-500 disabled:opacity-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200";

export function SceneMotion({ scene, index, disabled, saving, onChange }) {
  const file = scene.scene_image?.file || "";
  const still = /\.(png|jpe?g)(?:[?#].*)?$/i.test(file);
  const style = scene.motion_style || "NONE";
  const intensity = scene.motion_intensity || "SUBTLE";
  return <fieldset disabled={disabled || !still} className="mt-3 flex flex-wrap items-center gap-3 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
    <legend className="px-1 text-xs font-semibold text-gray-500 dark:text-gray-400">Image motion</legend>
    <label className="flex items-center gap-2 text-xs text-gray-500">Movement<select aria-label={`Motion for scene ${index + 1}`} value={style} onChange={event => onChange(scene, { motion_style: event.target.value, motion_intensity: intensity })} className={inputClass}>{styles.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    <label className="flex items-center gap-2 text-xs text-gray-500">Intensity<select aria-label={`Motion intensity for scene ${index + 1}`} disabled={style === "NONE"} value={intensity} onChange={event => onChange(scene, { motion_style: style, motion_intensity: event.target.value })} className={inputClass}><option value="SUBTLE">Subtle</option><option value="MEDIUM">Medium</option><option value="STRONG">Strong</option></select></label>
    <span role="status" className="text-xs text-gray-500 dark:text-gray-400">{saving ? "Saving motion…" : !still ? "Available for still images." : "Watch it in Preview video. Render again to export."}</span>
  </fieldset>;
}
