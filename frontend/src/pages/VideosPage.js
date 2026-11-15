import React, { useCallback, useRef, useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { HiOutlinePlus, HiOutlineFilm, HiOutlineChevronLeft, HiOutlineChevronRight } from "react-icons/hi2";
import { VideoLibraryToolbar } from "../components/VideoLibraryToolbar";
import { DefaultTable } from "../components/Table";
import { getVideos } from "../api/apiService";
import { libraryEmptyState } from "../utils/videoLibrary";
import { useDraftOwner } from "../hooks/useCreationDraft";
import { useVideoLibraryNavigation } from "../hooks/useVideoLibraryNavigation";

export const Videos = () => {
  const owner = useDraftOwner();
  return <VideoLibrary key={owner} owner={owner} />;
};

function VideoLibrary({ owner }) {
  const [videos, setVideos] = useState([]);
  const [readyQuery, setReadyQuery] = useState(null);
  const { query, queryKey, search, changeSearch, change } = useVideoLibraryNavigation(owner, readyQuery);
  const { search: debouncedSearchTerm, status: statusFilter, creation_mode: typeFilter, is_favorite: favoritesOnly, ordering, view, page: currentPage } = query;
  const [previousPage, setPreviousPage] = useState(null);
  const [nextPage, setNextPage] = useState(null);
  const [count, setCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const requestId = useRef(0);
  const fetchVideos = useCallback(async () => {
    const request = ++requestId.current;
    setIsLoading(true);
    const { data: response, status } = await getVideos(debouncedSearchTerm, currentPage, statusFilter, { creation_mode: typeFilter || undefined, is_favorite: favoritesOnly ? true : undefined, ordering });
    if (request !== requestId.current) return;
    if (!response && status === 404 && currentPage > 1) { change({ page: 1 }); return; }
    if (response) {
      setLoaded(true);
      setVideos(Array.isArray(response.results) ? response.results : []);
      setNextPage(response.next); setPreviousPage(response.previous); setCount(response.count || 0);
    }
    setFailed(!response); setIsLoading(false);
    if (response) setReadyQuery(queryKey);
  }, [debouncedSearchTerm, currentPage, statusFilter, typeFilter, favoritesOnly, ordering, queryKey]);
  useEffect(() => {
    fetchVideos();
    return () => { requestId.current += 1; };
  }, [fetchVideos]);

  const empty = libraryEmptyState(query);
  const filtered = !!debouncedSearchTerm || !!statusFilter || !!typeFilter || favoritesOnly;
  const clearFilters = () => change({ search: "", status: "", creation_mode: "", is_favorite: false });

  return <main className="video-library mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
    <header className="library-header mb-9 flex flex-wrap items-center justify-between gap-5">
      <div><p className="library-eyebrow mb-3"><HiOutlineFilm aria-hidden="true" className="h-4 w-4" />Your creative collection</p><h1 className="library-title text-gray-900 dark:text-white">My videos</h1><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Your stories, all in one place. Pick up where you left off.</p></div>
      <Link to="/" className="library-new-video inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900"><HiOutlinePlus aria-hidden="true" className="h-4 w-4" />New video</Link>
    </header>
    <section aria-label="Video library" aria-busy={isLoading}>
      {failed && loaded && <p role="alert" className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-900/20 dark:text-amber-200"><span>Could not update your videos. Your previous results are still shown.</span><button type="button" onClick={fetchVideos} className="font-semibold underline">Try again</button></p>}
      <VideoLibraryToolbar
        search={search} onSearch={changeSearch}
        status={statusFilter} onStatus={value => change({ status: value })}
        type={typeFilter} onType={value => change({ creation_mode: value })}
        favoritesOnly={favoritesOnly} onFavorites={value => change({ is_favorite: value })}
        ordering={ordering} onOrdering={value => change({ ordering: value })}
        view={view} onView={value => change({ view: value, page: currentPage })}
      />
      <div className="library-results-heading mb-5 flex items-center justify-between gap-3 px-1"><p aria-live="polite" className="text-xs text-gray-500 dark:text-gray-400">{isLoading ? "Loading videos…" : failed ? "" : `${count} ${count === 1 ? "video" : "videos"}${filtered ? " found" : " in your library"}`}</p>{filtered && <button type="button" onClick={clearFilters} className="rounded text-xs font-semibold text-blue-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-300">Clear filters</button>}</div>
      {failed && !isLoading && !loaded ? <div role="alert" className="rounded-2xl border border-gray-200 bg-white p-12 text-center dark:border-gray-700 dark:bg-gray-800"><h2 className="font-semibold text-gray-900 dark:text-white">Your videos could not be loaded</h2><p className="mt-2 text-sm text-gray-500">Please try again.</p><button type="button" onClick={fetchVideos} className="mt-5 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">Try again</button></div>
        : isLoading && !loaded ? <div role="status" className={view === "grid" ? "grid gap-5 sm:grid-cols-2 lg:grid-cols-3" : "space-y-3"}><span className="sr-only">Loading videos</span>{[1,2,3,4,5,6].map(item => <div key={item} className="overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"><div className={`animate-pulse bg-gray-100 dark:bg-gray-700 ${view === "grid" ? "aspect-video" : "h-20"}`} /><div className="space-y-3 p-4"><div className="h-3 w-1/2 animate-pulse rounded bg-gray-100 dark:bg-gray-700" /><div className="h-3 w-3/4 animate-pulse rounded bg-gray-100 dark:bg-gray-700" /></div></div>)}</div>
        : videos.length ? <DefaultTable data={videos} setVideos={setVideos} view={view} onUpdated={fetchVideos} favoritesOnly={favoritesOnly} />
        : <div className="rounded-2xl border border-dashed border-gray-300 px-6 py-16 text-center dark:border-gray-700"><div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-400 dark:bg-blue-500/10"><HiOutlineFilm aria-hidden="true" className="h-7 w-7" /></div><h2 className="font-semibold text-gray-900 dark:text-white">{empty.title}</h2><p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-gray-500 dark:text-gray-400">{empty.description}</p>{filtered ? <button type="button" onClick={clearFilters} className="mt-5 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500">{empty.action}</button> : <Link to="/" className="mt-5 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"><HiOutlinePlus aria-hidden="true" className="h-4 w-4" />Create your first video</Link>}</div>}
      {(count > 0 || currentPage > 1) && <footer className="mt-6 flex items-center justify-between gap-3 border-t border-gray-200 px-1 pt-4 dark:border-gray-700"><span className="text-xs text-gray-500 dark:text-gray-400">Page {currentPage}<span className="hidden sm:inline"> · {count} {count === 1 ? "video" : "videos"}{filtered ? " matching your filters" : " in your library"}</span></span><nav aria-label="Video pages" className="flex gap-2">{[[previousPage,"Previous",HiOutlineChevronLeft],[nextPage,"Next",HiOutlineChevronRight]].map(([page,label,Icon]) => <button key={label} type="button" disabled={!page || isLoading} onClick={() => change({ page })} className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">{label === "Previous" && <Icon aria-hidden="true" className="h-3 w-3" />}{label}{label === "Next" && <Icon aria-hidden="true" className="h-3 w-3" />}</button>)}</nav></footer>}
    </section>
  </main>;
};
