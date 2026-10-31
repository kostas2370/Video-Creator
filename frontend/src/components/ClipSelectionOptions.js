import { editorInput } from "./ui/EditorDialog";

export const clipFocusOptions = [
  { value: "general", label: "General highlights" },
  { value: "funny", label: "Funny moments" },
  { value: "advice", label: "Practical advice" },
  { value: "stories", label: "Stories" },
  { value: "debate", label: "Debates and opinions" },
];

export const clipSelectionModes = [
  { value: "fast", label: "Fast", description: "Uses the initial suggestions without an extra ranking review. Lower AI usage; repeated ideas may remain. Initial suggestions incur AI provider charges. Local transcription has no provider fee." },
  { value: "balanced", label: "Balanced", description: "Reviews multiple candidates for context, payoff, relevance, and repeated ideas. Adds AI usage when there is more than one candidate." },
  { value: "strict", label: "Strict", description: "Reviews every candidate with a higher acceptance bar. May return fewer clips or none. Adds AI usage." },
];

export function ClipSelectionOptions({ focus, mode, onFocusChange, onModeChange }) {
  return <div className="mt-5 grid gap-4 sm:grid-cols-2">
    <div>
      <label htmlFor="clip-focus" className="text-sm font-medium">Clip focus</label>
      <select id="clip-focus" aria-describedby="clip-focus-help" value={focus} onChange={event => onFocusChange(event.target.value)} className={`${editorInput} mt-2`}>
        {clipFocusOptions.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
      <p id="clip-focus-help" className="mt-2 text-xs leading-relaxed text-gray-500">Choose a starting preference. Your written request takes priority if it differs from this focus.</p>
    </div>
    <div>
      <label htmlFor="clip-selection-mode" className="text-sm font-medium">Selection mode</label>
      <select id="clip-selection-mode" aria-describedby="clip-selection-help" value={mode} onChange={event => onModeChange(event.target.value)} className={`${editorInput} mt-2`}>
        {clipSelectionModes.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
      <p id="clip-selection-help" className="mt-2 text-xs leading-relaxed text-gray-500">{clipSelectionModes.find(option => option.value === mode)?.description}</p>
    </div>
  </div>;
}
