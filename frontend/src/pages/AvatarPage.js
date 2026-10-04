import React, { useCallback, useState, useEffect } from "react";
import { HiOutlineMagnifyingGlass, HiOutlinePlus, HiOutlineUserGroup } from "react-icons/hi2";
import { getAvatars } from "../api/apiService";
import { Card } from "../components/ui/AvatarCards";
import { AvatarCreationModal } from "../components/AvatarCreationModal";
import { useDebounce } from "../hooks/useDebounce";

export const Avatar = () => {
  const [avatars, setAvatars] = useState([]);
  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  const debouncedSearchTerm = useDebounce(search, 500);
  const reload = useCallback(() => setRetry(value => value + 1), []);
  useEffect(() => {
    let current = true;
    setLoading(true);
    getAvatars(debouncedSearchTerm).then(({ data: response }) => {
      if (!current) return;
      setAvatars(Array.isArray(response) ? response : []);
      setFailed(!response); setLoading(false);
    });
    return () => { current = false; };
  }, [debouncedSearchTerm, retry]);
  return <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
    <AvatarCreationModal showModal={showModal} setShowModal={setShowModal} setAvatars={setAvatars} onCreated={reload} />
    <header className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-center"><div><p className="mb-2 text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-400">Your presenters</p><h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">Avatars</h1><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Give your stories a familiar face and a voice of their own.</p></div><button type="button" onClick={() => setShowModal(true)} className="flex w-fit items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700"><HiOutlinePlus className="h-5 w-5" />Create avatar</button></header>
    <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><p className="text-sm text-gray-500 dark:text-gray-400">{loading ? "Loading your presenters…" : `${avatars.length} ${avatars.length === 1 ? "avatar" : "avatars"}${debouncedSearchTerm ? " matching your search" : " available"}`}</p><div className="relative sm:w-80"><HiOutlineMagnifyingGlass aria-hidden="true" className="absolute left-3 top-3 h-5 w-5 text-gray-400" /><input type="search" aria-label="Search avatars" placeholder="Search avatars…" value={search} onChange={e => setSearch(e.target.value)} className="w-full rounded-xl border border-gray-200 bg-white py-2.5 pl-10 pr-3 text-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800" /></div></div>
    {loading ? <div role="status" className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3"><span className="sr-only">Loading avatars</span>{[1,2,3].map(i => <div key={i} className="h-80 animate-pulse rounded-2xl bg-gray-100 dark:bg-gray-800" />)}</div> : failed ? <div className="rounded-2xl border border-gray-200 bg-white p-12 text-center dark:border-gray-700 dark:bg-gray-800"><h2 className="font-semibold">Your avatars could not be loaded</h2><button type="button" onClick={reload} className="mt-4 text-sm font-semibold text-blue-600 dark:text-blue-400">Try again</button></div> : avatars.length ? <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{avatars.map(avatar => <Card key={avatar.id} imageSrc={avatar.file} title={avatar.name} audioSrc={avatar.sample} id={avatar.id} setAvatars={setAvatars} />)}</div> : <div className="rounded-2xl border border-dashed border-gray-300 p-12 text-center dark:border-gray-700"><HiOutlineUserGroup className="mx-auto mb-4 h-10 w-10 text-gray-300" /><h2 className="font-semibold text-gray-900 dark:text-white">{search ? "No matching avatars" : "Meet your next presenter"}</h2><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{search ? "Try another name or clear your search." : "Upload a portrait and choose a voice to create your first avatar."}</p><button type="button" onClick={() => search ? setSearch("") : setShowModal(true)} className="mt-5 text-sm font-semibold text-blue-600 dark:text-blue-400">{search ? "Clear search" : "Create your first avatar →"}</button></div>}
  </main>;
};
