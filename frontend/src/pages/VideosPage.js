import React, { useCallback, useRef, useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { HiOutlinePlus, HiOutlineFilm, HiOutlineChevronLeft, HiOutlineChevronRight } from "react-icons/hi2";
import { VideoLibraryToolbar } from "../components/VideoLibraryToolbar";
import { DefaultTable } from "../components/Table";
import { getVideos } from "../api/apiService";
import { libraryStatuses, libraryTypes, librarySorts } from "../utils/videoLibrary";
import { useDebounce } from "../hooks/useDebounce";

export const Videos = () => {
  const [searchParam, setSearchParam] = useSearchParams();
  const [videos, setVideos] = useState([]);
  const [statusFilter, setStatusFilter] = useState(libraryStatuses.some(item => item.value === searchParam.get("status")) ? searchParam.get("status") : "");
  const [typeFilter, setTypeFilter] = useState(libraryTypes.some(item => item.value === searchParam.get("creation_mode")) ? searchParam.get("creation_mode") : "");
  const [favoritesOnly, setFavoritesOnly] = useState(searchParam.get("is_favorite") === "true");
  const [ordering, setOrdering] = useState(librarySorts.some(item => item.value === searchParam.get("ordering")) ? searchParam.get("ordering") : "-updated_at");
  const [view, setView] = useState(searchParam.get("view") === "list" ? "list" : "grid");
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
    const { data: response, status } = await getVideos(debouncedSearchTerm, currentPage, statusFilter, { creation_mode: typeFilter || undefined, is_favorite: favoritesOnly ? true : undefined, ordering });
    if (request !== requestId.current) return;
    if (!response && status === 404 && currentPage > 1) { setCurrentPage(1); return; }
    if (response) {
      setVideos(Array.isArray(response.results) ? response.results : []);
      setNextPage(response.next); setPreviousPage(response.previous); setCount(response.count || 0);
    }
    setFailed(!response); setIsLoading(false);
  }, [debouncedSearchTerm, currentPage, statusFilter, typeFilter, favoritesOnly, ordering]);
  useEffect(() => {
    if (lastSearch.current !== debouncedSearchTerm) {
      lastSearch.current = debouncedSearchTerm;
      if (currentPage !== 1) { setCurrentPage(1); return; }
    }
    fetchVideos();
    return () => { requestId.current += 1; };
  }, [debouncedSearchTerm, currentPage, fetchVideos]);
  useEffect(() => {
    setSearchParam({ page: currentPage, search: debouncedSearchTerm, ...(statusFilter ? { status: statusFilter } : {}), ...(typeFilter ? { creation_mode: typeFilter } : {}), ...(favoritesOnly ? { is_favorite: "true" } : {}), ordering, ...(view === "list" ? { view } : {}) }, { replace: true });
  }, [currentPage, debouncedSearchTerm, statusFilter, typeFilter, favoritesOnly, ordering, view, setSearchParam]);

  const filtered = !!debouncedSearchTerm || !!statusFilter || !!typeFilter || favoritesOnly;
  const clearFilters = () => { setSearch(""); setStatusFilter(""); setTypeFilter(""); setFavoritesOnly(false); setCurrentPage(1); };

  return <main className="mx-auto max-w-6xl px-4 py-7 sm:px-6 sm:py-9">
    <header className="mb-7 flex flex-wrap items-center justify-between gap-4">
      <div><h1 className="text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl dark:text-white">My videos</h1><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Pick up a project or watch something you made.</p></div>
      <Link to="/" className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900"><HiOutlinePlus aria-hidden="true" className="h-4 w-4" />New video</Link>
    </header>
    <section aria-label="Video library">
      <VideoLibraryToolbar
        search={search} onSearch={setSearch}
        status={statusFilter} onStatus={value => { setStatusFilter(value); setCurrentPage(1); }}
        type={typeFilter} onType={value => { setTypeFilter(value); setCurrentPage(1); }}
        favoritesOnly={favoritesOnly} onFavorites={value => { setFavoritesOnly(value); setCurrentPage(1); }}
        ordering={ordering} onOrdering={value => { setOrdering(value); setCurrentPage(1); }}
        view={view} onView={setView}
      />
      <div className="mb-4 flex items-center justify-between gap-3 px-1"><p aria-live="polite" className="text-xs text-gray-500 dark:text-gray-400">{isLoading ? "Loading videos…" : failed ? "" : `${count} ${count === 1 ? "video" : "videos"}${filtered ? " found" : " in your library"}`}</p>{filtered && <button type="button" onClick={clearFilters} className="rounded text-xs font-semibold text-blue-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-300">Clear filters</button>}</div>
      {failed && !isLoading ? <div role="alert" className="rounded-2xl border border-gray-200 bg-white p-12 text-center dark:border-gray-700 dark:bg-gray-800"><h2 className="font-semibold text-gray-900 dark:text-white">Your videos could not be loaded</h2><p className="mt-2 text-sm text-gray-500">Please try again.</p><button type="button" onClick={fetchVideos} className="mt-5 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">Try again</button></div>
        : isLoading ? <div role="status" className={view === "grid" ? "grid gap-5 sm:grid-cols-2 lg:grid-cols-3" : "space-y-3"}><span className="sr-only">Loading videos</span>{[1,2,3,4,5,6].map(item => <div key={item} className="overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"><div className={`animate-pulse bg-gray-100 dark:bg-gray-700 ${view === "grid" ? "aspect-video" : "h-20"}`} /><div className="space-y-3 p-4"><div className="h-3 w-1/2 animate-pulse rounded bg-gray-100 dark:bg-gray-700" /><div className="h-3 w-3/4 animate-pulse rounded bg-gray-100 dark:bg-gray-700" /></div></div>)}</div>
        : videos.length ? <DefaultTable data={videos} setVideos={setVideos} view={view} onUpdated={fetchVideos} favoritesOnly={favoritesOnly} />
        : <div className="rounded-2xl border border-dashed border-gray-300 px-6 py-16 text-center dark:border-gray-700"><div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-400 dark:bg-blue-500/10"><HiOutlineFilm aria-hidden="true" className="h-7 w-7" /></div><h2 className="font-semibold text-gray-900 dark:text-white">{filtered ? "No videos match these filters" : "Your first video starts with an idea"}</h2><p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-gray-500 dark:text-gray-400">{filtered ? "Try a different search or filter to find your project." : "Create a story, bring your own clips, or let AI help you get started."}</p>{filtered ? <button type="button" onClick={clearFilters} className="mt-5 rounded-lg px-3 py-2 text-sm font-semibold text-blue-600 dark:text-blue-300">Clear filters</button> : <Link to="/" className="mt-5 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"><HiOutlinePlus aria-hidden="true" className="h-4 w-4" />Create your first video</Link>}</div>}
      {(count > 0 || currentPage > 1) && <footer className="mt-6 flex items-center justify-between gap-3 border-t border-gray-200 px-1 pt-4 dark:border-gray-700"><span className="text-xs text-gray-400">Page {currentPage}</span><nav aria-label="Video pages" className="flex gap-2">{[[previousPage,"Previous",HiOutlineChevronLeft],[nextPage,"Next",HiOutlineChevronRight]].map(([page,label,Icon]) => <button key={label} type="button" disabled={!page || isLoading} onClick={() => setCurrentPage(page)} className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">{label === "Previous" && <Icon aria-hidden="true" className="h-3 w-3" />}{label}{label === "Next" && <Icon aria-hidden="true" className="h-3 w-3" />}</button>)}</nav></footer>}
    </section>
  </main>;
};
