import { useId } from "react";

const languages = ["English", "Greek", "Spanish", "French", "German", "Italian", "Portuguese", "Arabic", "Hindi", "Chinese (Mandarin)", "Japanese", "Korean", "Dutch", "Polish", "Romanian", "Russian", "Turkish", "Ukrainian"];

export function NarrationLanguage({ value = "", onChange, disabled, className = "" }) {
  const id = `narration-language-${useId().replace(/:/g, "")}`;
  return <div><label htmlFor={id} className="block text-sm font-semibold">Narration language</label>
    <input id={id} type="text" list={`${id}-options`} maxLength={80} value={value} disabled={disabled} onChange={event => onChange(event.target.value)} placeholder="Automatic — match your prompt" aria-describedby={`${id}-help`} className={`${className} mt-2 font-normal`} />
    <datalist id={`${id}-options`}>{languages.map(language => <option key={language} value={language} />)}</datalist>
    <span id={`${id}-help`} className="mt-2 block text-xs font-normal leading-relaxed text-gray-500 dark:text-gray-400">Choose or type a language, including a regional variant. Leave blank to match your prompt. Applies to narration and spoken dialogue; choose a voice that supports it.</span>
  </div>;
}
