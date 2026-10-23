import { HiOutlineSparkles, HiOutlineClock, HiOutlineDocumentText } from "react-icons/hi2";
import { editorInput } from "./ui/EditorDialog";
import { descriptionBytes } from "../utils/youtubeMetadata";

const toolClass = "inline-flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-700 transition hover:border-blue-300 hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-40 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700";

export function VideoMetadataFields({ options, change, busy, onDescription, descriptionRevision, onUndoDescription }) {
  const bytes = descriptionBytes(options.caption);
  return <div className="space-y-5">
    <div>
      <div className="flex items-center justify-between gap-3"><label htmlFor="publish-title" className="text-sm font-semibold">Video title</label><span className="text-xs text-gray-500">{Array.from(options.title).length}/50</span></div>
      <input id="publish-title" required name="title" value={options.title} maxLength={50} onChange={change} className={`${editorInput} mt-2`} placeholder="Give viewers a reason to watch" />
    </div>
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2"><label htmlFor="publish-description" className="text-sm font-semibold">Description</label><span className={`text-xs ${bytes > 5000 ? "text-red-600" : "text-gray-500"}`}>{bytes.toLocaleString()}/5,000 bytes</span></div>
      <textarea id="publish-description" name="caption" value={options.caption} rows={7} maxLength={5000} onChange={change} className={`${editorInput} mt-2 resize-y`} placeholder="Tell viewers what this video covers. Generate a draft or start with a template below." />
      <div className="mt-2 flex flex-wrap gap-2">
        <button type="button" onClick={() => onDescription("generate")} className={toolClass}><HiOutlineSparkles className="h-4 w-4" />{busy === "description-generate" ? "Generating…" : "Generate description"}</button>
        <button type="button" onClick={() => onDescription("template")} className={toolClass}><HiOutlineDocumentText className="h-4 w-4" />{busy === "description-template" ? "Preparing…" : "Use script template"}</button>
        <button type="button" onClick={() => onDescription("timestamps")} className={toolClass}><HiOutlineClock className="h-4 w-4" />{busy === "description-timestamps" ? "Reading timing…" : "Add chapters"}</button>
        {descriptionRevision !== null && <button type="button" onClick={onUndoDescription} className={toolClass}>Undo description change</button>}
      </div>
      <p className="mt-2 text-xs leading-5 text-gray-500 dark:text-gray-400">Review every draft before publishing. Chapters use scene timing and need at least three sections of 10 seconds. The template uses your current script.</p>
    </div>
  </div>;
}
