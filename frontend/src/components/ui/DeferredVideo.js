import { useEffect, useRef, useState } from "react";

// Native video has no cross-browser lazy loading. Delay its source until it is
// near the viewport, including the clipped area of horizontal scene strips.
export function DeferredVideo({ src, preload = "metadata", ...props }) {
  const element = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") { setVisible(true); return; }
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        setVisible(true);
        observer.disconnect();
      }
    }, { rootMargin: "150px" });
    observer.observe(element.current);
    return () => observer.disconnect();
  }, []);
  return <video {...props} ref={element} src={visible ? src : undefined} preload={preload} />;
}
