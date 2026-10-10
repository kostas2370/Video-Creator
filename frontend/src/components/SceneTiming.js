import { formatDuration } from "../utils/timing";

const pauses = [0, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 5, 10];

export function SceneTiming({ scene, index, disabled, saving, onChange }) {
  const pause = scene.pause_after ?? 0;
  const options = pauses.includes(pause) ? pauses : [...pauses, pause].sort((a, b) => a - b);
  return <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-gray-50 px-4 py-3 dark:bg-gray-900/40">
    <div><p className="text-xs text-gray-500 dark:text-gray-400">Scene duration</p><p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{formatDuration(scene.timing?.duration)}</p></div>
    <label className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">Pause after scene
      <select aria-label={`Pause after scene ${index + 1}`} disabled={disabled} value={pause} onChange={event => onChange(scene, Number(event.target.value))} className="rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm text-gray-700 focus:ring-2 focus:ring-blue-500 disabled:opacity-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200">
        {options.map(value => <option key={value} value={value}>{value ? `${value}s` : "No extra pause"}</option>)}
      </select>
    </label>
    {saving && <span role="status" className="w-full text-xs text-blue-600 dark:text-blue-400">Saving timing…</span>}
  </div>;
}
