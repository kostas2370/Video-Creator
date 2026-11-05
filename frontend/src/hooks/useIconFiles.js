import { useEffect, useState } from "react";
import { getIcons } from "../api/apiService";

// Fetch just the artwork used by this diagram, not the whole catalog on every frame.
export function useIconFiles(keys) {
  const joined = [...new Set(keys.filter(Boolean))].sort().join(",");
  const [icons, setIcons] = useState({});
  useEffect(() => {
    let active = true;
    if (!joined) { setIcons({}); return; }
    getIcons({ keys: joined }).then(response => {
      if (active && response.ok) setIcons(Object.fromEntries(response.data.results.map(icon => [icon.key, icon])));
    });
    return () => { active = false; };
  }, [joined]);
  return icons;
}
