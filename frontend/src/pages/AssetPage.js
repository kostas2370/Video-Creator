import React, { useEffect, useState } from "react";
import { HiOutlineMagnifyingGlass, HiOutlinePlus } from "react-icons/hi2";
import { getIntro, getOutro, createIntro, createOutro, deleteIntro, deleteOutro } from "../api/apiService";
import { SmallTable } from "../components/SmallTable";
import { AssetCreationModal } from "../components/AssetCreationModal";
import { useDebounce } from "../hooks/useDebounce";

function AssetCollection({ name, getItems, createItem, deleteItem, active }) {
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  const term = useDebounce(search, 500);
  useEffect(() => {
    let current = true; setLoading(true);
    getItems(term).then(({ data: response }) => {
      if (!current) return;
      setItems(Array.isArray(response) ? response : []); setFailed(!response); setLoading(false);
    });
    return () => { current = false; };
  }, [term, retry, getItems]);
  const plural = name === "Intro" ? "Intros" : "Outros";
  return <section role="tabpanel" id={`${name}-panel`} aria-labelledby={`${name}-tab`} hidden={!active}>
    <AssetCreationModal showModal={showModal} setShowModal={setShowModal} nameh1={name} ApiCall={createItem} setItems={setItems} onCreated={() => setRetry(value => value + 1)} />
    <div className="flex flex-col justify-between gap-4 border-b border-gray-100 p-5 sm:flex-row sm:items-center dark:border-gray-700"><div><h2 className="font-semibold text-gray-900 dark:text-white">{plural}</h2><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{name === "Intro" ? "Set the scene before your story begins." : "Leave a lasting impression at the end."}</p></div><div className="flex flex-wrap items-center gap-3"><div className="relative min-w-0 flex-1 sm:w-64"><HiOutlineMagnifyingGlass aria-hidden="true" className="absolute left-3 top-3 h-5 w-5 text-gray-400" /><input type="search" aria-label={`Search ${plural.toLowerCase()}`} placeholder={`Search ${plural.toLowerCase()}…`} value={search} onChange={e => setSearch(e.target.value)} className="w-full rounded-xl border border-gray-200 bg-gray-50 py-2.5 pl-10 pr-3 text-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-900" /></div><button type="button" onClick={() => setShowModal(true)} className="flex shrink-0 items-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700"><HiOutlinePlus />Add {name.toLowerCase()}</button></div></div>
    {loading ? <div role="status" className="space-y-3 p-5"><span className="sr-only">Loading {plural.toLowerCase()}</span>{[1,2].map(i => <div key={i} className="h-16 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-700" />)}</div> : failed ? <div className="p-12 text-center"><h3 className="font-semibold">Your {plural.toLowerCase()} could not be loaded</h3><button type="button" onClick={() => setRetry(value => value + 1)} className="mt-4 text-sm font-semibold text-blue-600 dark:text-blue-400">Try again</button></div> : items.length ? <SmallTable data={items} setData={setItems} deleteFunction={deleteItem} name={name} /> : <div className="p-12 text-center"><h3 className="font-semibold text-gray-900 dark:text-white">{term ? `No matching ${plural.toLowerCase()}` : `Add your first ${name.toLowerCase()}`}</h3><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{term ? "Try another name or clear your search." : "Upload a reusable clip, then select it in your video settings."}</p><button type="button" onClick={() => term ? setSearch("") : setShowModal(true)} className="mt-5 text-sm font-semibold text-blue-600 dark:text-blue-400">{term ? "Clear search" : `Upload ${name.toLowerCase()} →`}</button></div>}
  </section>;
}

export const AssetPage = () => {
  const [tab, setTab] = useState("Intro");
  const tabs = ["Intro", "Outro"];
  const moveTab = (event, index) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? 1 : (index + 1) % 2;
    setTab(tabs[next]); document.getElementById(`${tabs[next]}-tab`)?.focus();
  };
  return <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6"><header className="mb-8"><p className="mb-2 text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-400">Your media library</p><h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">My assets</h1><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Keep your opening and closing clips ready for every story.</p></header>
    <div className="mb-5 flex w-fit gap-1 rounded-xl bg-gray-100 p-1 dark:bg-gray-800" role="tablist" aria-label="Asset type">{tabs.map((name,index) => <button type="button" key={name} role="tab" id={`${name}-tab`} aria-controls={`${name}-panel`} aria-selected={tab === name} tabIndex={tab === name ? 0 : -1} onKeyDown={e => moveTab(e,index)} onClick={() => setTab(name)} className={`rounded-lg px-6 py-2.5 text-sm font-semibold ${tab === name ? "bg-white text-blue-600 shadow-sm dark:bg-gray-700 dark:text-blue-300" : "text-gray-500 dark:text-gray-400"}`}>{name}s</button>)}</div>
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800"><AssetCollection name="Intro" getItems={getIntro} createItem={createIntro} deleteItem={deleteIntro} active={tab === "Intro"} /><AssetCollection name="Outro" getItems={getOutro} createItem={createOutro} deleteItem={deleteOutro} active={tab === "Outro"} /></div>
  </main>;
};
