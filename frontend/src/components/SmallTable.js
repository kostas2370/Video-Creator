import { useState } from "react";
import { HiOutlineFilm, HiOutlineArrowTopRightOnSquare, HiOutlineTrash } from "react-icons/hi2";
import { DeleteModal } from "./DeleteModal";

export function SmallTable({ data, setData, deleteFunction, name = "Asset" }) {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [id, setId] = useState(null);
  return <>
    <DeleteModal showModal={showDeleteModal} setShowModal={setShowDeleteModal} id={id} setItems={setData} name={name} mode="normal" deleteFunction={deleteFunction} />
    <ul className="divide-y divide-gray-100 dark:divide-gray-700">{data?.map(row => <li key={row.id} className="flex flex-wrap items-center gap-4 px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-900/20"><span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-500 dark:bg-blue-900/30"><HiOutlineFilm className="h-5 w-5" /></span><div className="min-w-0 flex-1"><h3 className="break-words text-sm font-semibold text-gray-900 dark:text-white">{row.name}</h3><p className="mt-1 text-xs text-gray-400">{name} clip</p></div><div className="ml-auto flex items-center gap-2"><a target="_blank" rel="noreferrer" href={row.file} aria-label={`Preview ${row.name}`} className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium text-gray-600 hover:text-blue-600 dark:border-gray-600 dark:text-gray-300">Preview<HiOutlineArrowTopRightOnSquare className="h-4 w-4" /></a><button type="button" aria-label={`Delete ${row.name}`} onClick={() => { setId(row.id); setShowDeleteModal(true); }} className="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30"><HiOutlineTrash className="h-4 w-4" /></button></div></li>)}</ul>
  </>;
}
