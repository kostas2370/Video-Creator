import { Popover, PopoverButton, PopoverPanel } from "@headlessui/react";
import {
  HiOutlineMagnifyingGlass, HiOutlineAdjustmentsHorizontal, HiOutlineStar,
  HiOutlineSquares2X2, HiOutlineBars3, HiOutlineChevronDown, HiOutlineXMark,
} from "react-icons/hi2";
import { libraryStatuses, libraryTypes, librarySorts } from "../utils/videoLibrary";

const focus = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500";
const control = `inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-3 text-sm font-medium text-gray-600 transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700 ${focus}`;
const select = "w-full appearance-none rounded-xl border border-gray-200 bg-white py-2.5 pl-3 pr-9 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white";

export function VideoLibraryToolbar({ search, onSearch, status, onStatus, type, onType,
  favoritesOnly, onFavorites, ordering, onOrdering, view, onView }) {
  const active = [
    status && { label: libraryStatuses.find(item => item.value === status)?.label, clear: () => onStatus("") },
    type && { label: libraryTypes.find(item => item.value === type)?.label, clear: () => onType("") },
  ].filter(Boolean);

  return <div className="mb-5 space-y-4">
    <div role="group" aria-label="Video collection" className="flex gap-6 border-b border-gray-200 dark:border-gray-700">
      {[[false, "All videos"], [true, "Favorites"]].map(([value, label]) =>
        <button key={label} type="button" aria-pressed={favoritesOnly === value} onClick={() => onFavorites(value)} className={`relative -mb-px inline-flex min-h-11 items-center gap-2 border-b-2 px-1 pb-3 pt-1 text-sm font-semibold transition ${focus} ${favoritesOnly === value ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-300" : "border-transparent text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"}`}>
          {value && <HiOutlineStar aria-hidden="true" className="h-4 w-4" />}{label}
        </button>
      )}
    </div>
    <div className="flex flex-wrap items-center gap-2 sm:gap-3">
      <div className="relative w-full sm:mr-auto sm:w-auto sm:min-w-52 sm:max-w-sm sm:flex-1">
        <HiOutlineMagnifyingGlass aria-hidden="true" className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-gray-400" />
        <input type="search" aria-label="Search videos" placeholder="Search your videos…" value={search} onChange={event => onSearch(event.target.value)} className="h-10 w-full rounded-xl border border-gray-200 bg-white pl-10 pr-3 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-white" />
      </div>
      <Popover>
        <PopoverButton className={`${control} data-[open]:border-blue-400 data-[open]:text-blue-600 dark:data-[open]:text-blue-300`}>
          <HiOutlineAdjustmentsHorizontal aria-hidden="true" className="h-4 w-4" />Filters
          {active.length > 0 && <span className="flex h-5 min-w-5 items-center justify-center rounded-md bg-blue-50 px-1 text-[11px] font-bold text-blue-700 dark:bg-blue-500/20 dark:text-blue-300">{active.length}<span className="sr-only"> active</span></span>}
        </PopoverButton>
        <PopoverPanel anchor={{ to: "bottom start", gap: 8, padding: 16 }} className="z-50 w-72 max-w-[calc(100vw-2rem)] rounded-2xl border border-gray-200 bg-white p-4 shadow-xl focus:outline-none dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-4 flex items-center justify-between"><h2 className="text-sm font-semibold text-gray-900 dark:text-white">Filter videos</h2>{active.length > 0 && <button type="button" onClick={() => { onStatus(""); onType(""); }} className={`rounded text-xs font-semibold text-blue-600 dark:text-blue-300 ${focus}`}>Reset</button>}</div>
          <div className="space-y-4">
            {[["Status", "Filter videos by status", status, onStatus, libraryStatuses], ["Video type", "Filter videos by type", type, onType, libraryTypes]].map(([label, ariaLabel, value, onChange, options]) =>
              <label key={label} className="block"><span className="mb-1.5 block text-xs font-medium text-gray-500 dark:text-gray-400">{label}</span><span className="relative block"><select aria-label={ariaLabel} value={value} onChange={event => onChange(event.target.value)} className={select}>{options.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select><HiOutlineChevronDown aria-hidden="true" className="pointer-events-none absolute right-3 top-3.5 h-4 w-4 text-gray-400" /></span></label>
            )}
          </div>
        </PopoverPanel>
      </Popover>
      <div className="relative min-w-0 flex-1 sm:flex-none">
        <select aria-label="Sort videos" value={ordering} onChange={event => onOrdering(event.target.value)} className={`${select} h-10 py-0 sm:w-44`}>{librarySorts.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
        <HiOutlineChevronDown aria-hidden="true" className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-gray-400" />
      </div>
      <div role="group" aria-label="Library layout" className="flex shrink-0 gap-0.5 rounded-xl border border-gray-200 bg-gray-50 p-1 dark:border-gray-700 dark:bg-gray-800">
        {[["grid", "Grid view", HiOutlineSquares2X2], ["list", "List view", HiOutlineBars3]].map(([value, label, Icon]) => <button key={value} type="button" aria-label={label} title={label} aria-pressed={view === value} onClick={() => onView(value)} className={`rounded-lg p-1.5 transition ${focus} ${view === value ? "bg-white text-blue-600 shadow-sm dark:bg-gray-700 dark:text-blue-300" : "text-gray-400 hover:text-gray-700 dark:hover:text-white"}`}><Icon aria-hidden="true" className="h-4 w-4" /></button>)}
      </div>
    </div>
    {active.length > 0 && <div role="group" aria-label="Active filters" className="flex flex-wrap gap-2">{active.map(({ label, clear }) => <button key={label} type="button" aria-label={`Remove ${label} filter`} onClick={clear} className={`inline-flex items-center gap-1.5 rounded-lg bg-blue-50 px-2.5 py-1.5 text-xs font-medium text-blue-700 transition hover:bg-blue-100 dark:bg-blue-500/10 dark:text-blue-300 dark:hover:bg-blue-500/20 ${focus}`}>{label}<HiOutlineXMark aria-hidden="true" className="h-3.5 w-3.5" /></button>)}</div>}
  </div>;
}
