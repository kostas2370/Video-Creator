export function GenerationModeSelect({ value = "STANDARD", onChange, disabled = false }) {
  return <div className="rounded-xl border border-gray-200 p-4 dark:border-gray-700">
    <label className="block text-sm font-semibold">Generation mode
      <select value={value} disabled={disabled} onChange={event => onChange(event.target.value)} className="mt-2 block w-full rounded-xl border border-gray-300 bg-white p-3 text-sm text-gray-900 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-900 dark:text-white">
        <option value="STANDARD">Standard</option>
        <option value="ECONOMY">Economy — lower-cost images</option>
      </select>
    </label>
    <p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">{value === "ECONOMY" ? "Uses medium quality for new OpenAI images and starting frames, or low if already configured. Less detail, lower image cost. Animation and narration prices are unchanged." : "Uses the configured image quality. Choose Economy when you want lower-cost OpenAI images and starting frames."} Existing media is kept; switching modes makes no paid request.</p>
  </div>;
}
