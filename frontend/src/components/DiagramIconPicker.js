import { useState } from "react";
import { useIconFiles } from "../hooks/useIconFiles";
import { IconUpload } from "./IconUpload";
import { IconLibrary } from "./IconLibrary";

export function DiagramIconPicker({ value = "", onChange, index }) {
  const [open, setOpen] = useState(false);
  const selected = useIconFiles([value])[value];
  const choose = key => { onChange(key); setOpen(false); };
  return <div>
    <button type="button" aria-expanded={open} aria-label={`Icon for item ${index + 1}: ${selected?.name || (value ? "Selected icon" : "None")}`} onClick={() => setOpen(current => !current)} className="flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600">
      {selected && <img src={selected.file} alt="" className="h-8 w-8 rounded bg-slate-800 p-1" />}
      Icon: {selected?.name || (value ? "Selected icon" : "None")}
    </button>
    {open && <div className="mt-2 space-y-2 rounded-lg border border-gray-200 p-3 dark:border-gray-600">
      <button type="button" onClick={() => choose("")} className="text-sm text-blue-600 dark:text-blue-300">No icon</button>
      <IconUpload index={index} onUploaded={icon => choose(icon.key)} />
      <IconLibrary compact searchLabel={`Search icons for item ${index + 1}`} selectedKey={value} onSelect={icon => choose(icon.key)} />
    </div>}
  </div>;
}
