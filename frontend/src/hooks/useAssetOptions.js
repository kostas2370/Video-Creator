import { useCallback, useEffect, useRef, useState } from "react";

// Load another bounded page only when the user asks for more choices.
export function useAssetOptions(getPage, enabled = true) {
  const [items, setItems] = useState([]);
  const [next, setNext] = useState(1);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const generation = useRef(0);
  const pending = useRef(false);
  const load = useCallback(async (page, replace = false) => {
    if (pending.current) return;
    pending.current = true;
    const token = generation.current;
    setLoading(true);
    const response = await getPage(undefined, page);
    if (token !== generation.current) return;
    if (response.ok) {
      const rows = response.data.results;
      setItems(previous => replace ? rows : [...previous, ...rows.filter(row => !previous.some(existing => existing.id === row.id))]);
      setNext(response.data.next);
      setFailed(false);
    } else setFailed(true);
    pending.current = false;
    setLoading(false);
  }, [getPage]);
  useEffect(() => {
    generation.current += 1;
    pending.current = false;
    if (enabled) { setItems([]); setFailed(false); setNext(1); load(1, true); }
    return () => { generation.current += 1; pending.current = false; };
  }, [enabled, load]);
  return { items, setItems, loading, failed, hasMore: next !== null, loadMore: () => load(next ?? 1, next === 1) };
}
