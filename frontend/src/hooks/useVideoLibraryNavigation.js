import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { libraryQuery, libraryQueryString, readLibraryNavigation, saveLibraryNavigation } from "../utils/videoLibraryNavigation";

export function useVideoLibraryNavigation(owner, readyQuery) {
  const [params, setParams] = useSearchParams();
  const [saved] = useState(() => readLibraryNavigation(owner));
  const restoreQuery = useRef(!params.toString() && !!saved?.query);
  const query = libraryQuery(restoreQuery.current ? saved.query : params.toString());
  const queryKey = libraryQueryString(query);
  const [search, setSearch] = useState(query.search);
  const currentQuery = useRef(query);
  currentQuery.current = query;
  const currentSearch = useRef(search);
  currentSearch.current = search;
  const timer = useRef(null);
  const previousQuery = useRef(queryKey);
  const position = useRef(saved?.query === queryKey ? saved.scrollY : 0);
  const scrollReady = useRef(false);
  const latest = useRef({ query: queryKey, scrollY: position.current });

  useEffect(() => {
    if (restoreQuery.current) { restoreQuery.current = false; setParams(saved.query, { replace: true }); }
  }, [saved, setParams]);
  useEffect(() => {
    clearTimeout(timer.current);
    setSearch(query.search);
    if (previousQuery.current !== queryKey) {
      position.current = 0;
      scrollReady.current = false;
      previousQuery.current = queryKey;
    }
  }, [queryKey, query.search]);

  const rememberedQuery = search === query.search ? queryKey : libraryQueryString({ ...query, search, page: 1 });
  latest.current = { query: rememberedQuery, scrollY: position.current };
  useEffect(() => { saveLibraryNavigation(owner, latest.current); }, [owner, rememberedQuery]);
  useEffect(() => {
    const onScroll = () => {
      if (!scrollReady.current) return;
      position.current = Math.max(0, window.scrollY);
      latest.current = { ...latest.current, scrollY: position.current };
    };
    const save = () => saveLibraryNavigation(owner, latest.current);
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("pagehide", save);
    return () => { clearTimeout(timer.current); save(); window.removeEventListener("scroll", onScroll); window.removeEventListener("pagehide", save); };
  }, [owner]);
  useLayoutEffect(() => {
    if (readyQuery !== queryKey) return;
    const frame = requestAnimationFrame(() => {
      window.scrollTo({ top: position.current, left: 0, behavior: "instant" });
      scrollReady.current = true;
    });
    return () => cancelAnimationFrame(frame);
  }, [readyQuery, queryKey]);

  const change = changes => {
    clearTimeout(timer.current);
    const nextQuery = { ...currentQuery.current, search: currentSearch.current, page: 1, ...changes };
    const next = libraryQueryString(nextQuery);
    if (next === libraryQueryString(currentQuery.current)) return;
    currentQuery.current = nextQuery;
    position.current = 0;
    scrollReady.current = false;
    setParams(next, { replace: true });
  };
  const changeSearch = value => {
    currentSearch.current = value;
    setSearch(value);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => change({ search: value }), 500);
  };
  return { query, queryKey, search, changeSearch, change };
}
