import { editorInput } from "./ui/EditorDialog";
import { videoFonts, videoFontFamily } from "../utils/fonts";

export function FontPicker({ value = "DejaVu Sans", fonts = videoFonts, onChange }) {
  return <label className="block text-sm">Font
    <select value={value} onChange={event => onChange(event.target.value)} style={{ fontFamily: videoFontFamily(value) }} className={`${editorInput} mt-2`}>
      {fonts.map(font => <option key={font} value={font} style={{ fontFamily: videoFontFamily(font) }}>{font}</option>)}
    </select>
    <span aria-hidden="true" className="mt-2 block rounded-lg bg-gray-50 px-3 py-2 text-lg text-gray-700 dark:bg-gray-900/40 dark:text-gray-200" style={{ fontFamily: videoFontFamily(value) }}>Aa · Make every word count</span>
  </label>;
}
