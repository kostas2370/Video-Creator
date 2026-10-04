import React, { useCallback, useRef, useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { HiOutlineMagnifyingGlass, HiOutlinePlus, HiOutlineFilm } from "react-icons/hi2";
import { DefaultTable } from "../components/Table";
import { getVideos } from "../api/apiService";
import { useDebounce } from "../hooks/useDebounce";

export const Videos = () => {
  const [searchParam, setSearchParam] = useSearchParams();
  const [videos, setVideos] = useState([]);
  const [search, setSearch] = useState(searchParam.get("search") || "");
  const debouncedSearchTerm = useDebounce(search, 500);
  const [currentPage, setCurrentPage] = useState(Number(searchParam.get("page")) || 1);
  const [previousPage, setPreviousPage] = useState(null);
  const [nextPage, setNextPage] = useState(null);
  const [count, setCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const requestId = useRef(0);
  const lastSearch = useRef(debouncedSearchTerm);
  const fetchVideos = useCallback(async () => {
    const request = ++requestId.current;
    setIsLoading(true);
    const { data: response } = await getVideos(debouncedSearchTerm, currentPage);
    if (request !== requestId.current) return;
    if (response) {
      setVideos(Array.isArray(response.results) ? response.results : []);
      setNextPage(response.next); setPreviousPage(response.previous); setCount(response.count || 0);
    }
    setFailed(!response); setIsLoading(false);
  }, [debouncedSearchTerm, currentPage]);
  useEffect(() => {
    if (lastSearch.current !== debouncedSearchTerm) {
      lastSearch.current = debouncedSearchTerm;
      if (currentPage !== 1) { setCurrentPage(1); return; }
    }
    fetchVideos();
    return () => { requestId.current += 1; };
  }, [debouncedSearchTerm, currentPage, fetchVideos]);
  useEffect(() => {
    setSearchParam({ page: currentPage, search: debouncedSearchTerm }, { replace: true });
  }, [currentPage, debouncedSearchTerm, setSearchParam]);

  return <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
    <header className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
      <div><p className="mb-2 text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-400">Your library</p><h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">My videos</h1><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">All your stories in one place. Pick up a draft or watch the finished video.</p></div>
      <Link to="/" className="inline-flex w-fit items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"><HiOutlinePlus className="h-5 w-5" />Create video</Link>
    </header>
    <section aria-label="Video library" className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="flex flex-col justify-between gap-4 border-b border-gray-100 p-5 sm:flex-row sm:items-center dark:border-gray-700">
        <div><h2 className="font-semibold text-gray-900 dark:text-white">All videos</h2><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{isLoading ? "Loading your library…" : `${count} ${count === 1 ? "video" : "videos"}${debouncedSearchTerm ? " matching your search" : " in your library"}`}</p></div>
        <div className="relative sm:w-80"><HiOutlineMagnifyingGlass aria-hidden="true" className="pointer-events-none absolute left-3 top-3 h-5 w-5 text-gray-400" /><input type="search" aria-label="Search videos" placeholder="Search videos…" value={search} onChange={e => setSearch(e.target.value)} className="w-full rounded-xl border border-gray-200 bg-gray-50 py-2.5 pl-10 pr-3 text-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white" /></div>
      </div>
      {failed && !isLoading ? <div className="p-12 text-center"><h3 className="font-semibold text-gray-900 dark:text-white">Your videos could not be loaded</h3><p className="mt-2 text-sm text-gray-500">Please try again.</p><button type="button" onClick={fetchVideos} className="mt-5 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">Try again</button></div> : isLoading ? <div role="status" className="space-y-4 p-5"><span className="sr-only">Loading videos</span>{[1,2,3].map(i => <div key={i} className="h-20 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-700" />)}</div> : videos.length ? <DefaultTable data={videos} setVideos={setVideos} /> : <div className="p-12 text-center"><HiOutlineFilm className="mx-auto mb-4 h-10 w-10 text-gray-300" /><h3 className="font-semibold text-gray-900 dark:text-white">{debouncedSearchTerm ? "No matching videos" : "Your first video starts with an idea"}</h3><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{debouncedSearchTerm ? "Try a different title or clear your search." : "Generate a story, edit your scenes, and make it yours."}</p>{debouncedSearchTerm ? <button type="button" onClick={() => setSearch("")} className="mt-5 text-sm font-semibold text-blue-600 dark:text-blue-400">Clear search</button> : <Link to="/" className="mt-5 inline-block text-sm font-semibold text-blue-600 dark:text-blue-400">Create your first video →</Link>}</div>}
      <footer className="flex items-center justify-between gap-3 border-t border-gray-100 px-5 py-4 dark:border-gray-700"><span className="text-xs text-gray-500 dark:text-gray-400">Page {currentPage}</span><nav aria-label="Video pages" className="flex gap-2">{[[previousPage,"Previous"],[nextPage,"Next"]].map(([page,label]) => <button key={label} type="button" disabled={!page || isLoading} onClick={() => setCurrentPage(page)} className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700">{label}</button>)}</nav></footer>
    </section>
  </main>;
};
