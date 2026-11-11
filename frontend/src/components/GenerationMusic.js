export function GenerationMusic({ value = "", onChange, className }) {
  const automatic = value === "auto";
  return <div>
    <label className="mt-2 flex cursor-pointer items-start gap-2 text-sm"><input type="checkbox" checked={automatic} onChange={event => onChange(event.target.checked ? "auto" : "")} className="mt-1 accent-blue-600" /><span>Auto-select music<span className="mt-1 block text-xs text-gray-500 dark:text-gray-400">Pick general music using your video's topic and mood.</span></span></label>
    {!automatic && <input type="url" aria-label="Background music YouTube link" id="music" name="music" value={value} onChange={event => onChange(event.target.value)} className={className} placeholder="Or paste a YouTube URL (optional)" />}
  </div>;
}
