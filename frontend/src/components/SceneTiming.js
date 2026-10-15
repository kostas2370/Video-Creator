import { useEffect, useState } from "react";
import { formatDuration } from "../utils/timing";

const pauses = [0, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 5, 10];

export function SceneTiming({ manual, scene, index, disabled, saving, onChange }) {
  const override = scene.audio_settings?.duration ?? null;
  const [duration, setDuration] = useState(override ?? "");
  useEffect(() => setDuration(override ?? ""), [override]);
  const pause = scene.pause_after ?? 0;
  const options = pauses.includes(pause) ? pauses : [...pauses, pause].sort((a, b) => a - b);
  return <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-gray-50 px-4 py-3 dark:bg-gray-900/40">
    <div><p className="text-xs text-gray-500 dark:text-gray-400">Scene duration</p><p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{formatDuration(scene.timing?.duration)}</p></div>
    {manual && <label className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">Duration (s)<input aria-label={`Duration of scene ${index + 1}`} type="number" min="0.1" max="900" step="0.1" placeholder="Auto" value={duration} disabled={disabled} onChange={event => setDuration(event.target.value)} onBlur={async event => { const value = duration === "" ? null : Number(duration); if (event.target.validity.valid && value !== override && await onChange(scene, { duration: value }) === false) setDuration(override ?? ""); }} className="w-24 rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-800" /></label>}
    <label className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">Pause after scene
      <select aria-label={`Pause after scene ${index + 1}`} disabled={disabled} value={pause} onChange={event => onChange(scene, { pause_after: Number(event.target.value) })} className="rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm text-gray-700 focus:ring-2 focus:ring-blue-500 disabled:opacity-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200">
        {options.map(value => <option key={value} value={value}>{value ? `${value}s` : "No extra pause"}</option>)}
      </select>
    </label>
    {saving && <span role="status" className="w-full text-xs text-blue-600 dark:text-blue-400">Saving timing…</span>}
  </div>;
}
