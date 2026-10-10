import { API_HOST } from "../../endpoints";
import { Listbox, ListboxButton, ListboxLabel, ListboxOption, ListboxOptions } from "@headlessui/react";
import { RiAddLine, RiArrowDownSLine, RiCheckLine, RiFilmLine } from "react-icons/ri";

function ScenePreview({ scene, number }) {
  const image = scene?.scene_image?.file;
  return <div className="flex min-w-0 flex-1 items-center gap-2.5 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
    <span className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-gray-100 text-gray-400 dark:bg-gray-700">
      {image && /\.(png|jpe?g|webp)(\?|$)/i.test(image) ? <img src={API_HOST + image} alt="" className="h-full w-full object-cover" /> : <RiFilmLine className="h-4 w-4" />}
    </span>
    <div className="min-w-0"><p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">Scene {number}</p><p className="truncate text-xs text-gray-600 dark:text-gray-300">{scene.text || "Untitled scene"}</p></div>
  </div>;
}

export function ScenePositionPicker({ scenes, value, onChange, count = 1, disabled = false }) {
  const index = value ? scenes.findIndex(scene => String(scene.position) === value) : scenes.length;
  const slot = index < 0 ? scenes.length : index;
  const previous = scenes[slot - 1];
  const next = scenes[slot];
  const label = next ? `Before scene ${slot + 1}` : scenes.length ? "At the end" : "First scene";
  return <section className="rounded-2xl border border-gray-200 bg-gray-50/70 p-4 dark:border-gray-700 dark:bg-gray-900/30">
    <Listbox disabled={disabled} value={value} onChange={onChange}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><ListboxLabel className="block text-sm font-semibold text-gray-900 dark:text-white">Insert position</ListboxLabel><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Choose where this moment fits.</p></div>
        <ListboxButton className="flex min-w-[160px] items-center justify-between gap-4 rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm font-medium text-gray-800 shadow-sm outline-none transition hover:border-blue-300 focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100">
          {label}<RiArrowDownSLine className="h-4 w-4 text-gray-400" />
        </ListboxButton>
      </div>
      <ListboxOptions anchor={{ to: "bottom end", gap: 8 }} className="z-[70] max-h-64 w-[min(360px,calc(100vw-3rem))] overflow-y-auto rounded-xl border border-gray-200 bg-white p-1.5 shadow-xl outline-none dark:border-gray-600 dark:bg-gray-800">
        {[{ value: "", label: scenes.length ? "At the end" : "First scene", detail: scenes.length ? `After scene ${scenes.length}` : "Start your story" }, ...scenes.map((scene, i) => ({ value: String(scene.position), label: `Before scene ${i + 1}`, detail: scene.text || "Untitled scene" }))].map(option => <ListboxOption key={option.value} value={option.value} className="group flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-gray-700 data-[focus]:bg-blue-50 data-[selected]:text-blue-700 dark:text-gray-200 dark:data-[focus]:bg-gray-700 dark:data-[selected]:text-blue-300">
          <div className="min-w-0 flex-1"><p className="text-sm font-medium">{option.label}</p><p className="mt-0.5 truncate text-xs text-gray-400">{option.detail}</p></div><RiCheckLine className="h-4 w-4 shrink-0 opacity-0 group-data-[selected]:opacity-100" />
        </ListboxOption>)}
      </ListboxOptions>
    </Listbox>
    <div className="mt-4 flex flex-col items-stretch gap-2 sm:flex-row" aria-label="Scene order preview">
      {previous && <ScenePreview scene={previous} number={slot} />}
      <div className="flex min-w-0 flex-1 items-center justify-center gap-2 rounded-xl border border-dashed border-blue-300 bg-blue-50 p-3 text-blue-700 dark:border-blue-700 dark:bg-blue-900/20 dark:text-blue-300"><RiAddLine className="h-4 w-4 shrink-0" /><div><p className="text-xs font-semibold">{count > 1 ? `${count} new scenes` : "New scene"}</p><p className="mt-0.5 text-[11px] opacity-70">{count > 1 ? `Positions ${slot + 1}–${slot + count}` : `Position ${slot + 1}`}</p></div></div>
      {next && <ScenePreview scene={next} number={slot + 1} />}
    </div>
  </section>;
}
