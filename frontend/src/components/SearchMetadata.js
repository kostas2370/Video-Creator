import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { publicPages, siteOrigin } from "../content/search.mjs";

function meta(attribute, name, value) {
  const selector = `meta[${attribute}="${name}"]`;
  let element = document.head.querySelector(selector);
  if (value === null) {
    element?.remove();
    return;
  }
  if (!element) {
    element = document.createElement("meta");
    element.setAttribute(attribute, name);
    document.head.appendChild(element);
  }
  element.content = value;
}

export default function SearchMetadata() {
  const { pathname } = useLocation();
  useEffect(() => {
    const path = pathname === "/" ? "/" : `${pathname.replace(/\/+$/, "")}/`;
    const page = publicPages[path];
    const origin = siteOrigin(
      import.meta.env.VITE_PUBLIC_SITE_URL || window.location.origin,
    );
    meta("name", "robots", page ? "index, follow" : "noindex, nofollow");
    let canonical = document.head.querySelector('link[rel="canonical"]');
    if (page) {
      document.title = page.title;
      meta("name", "description", page.description);
      meta("property", "og:title", page.title);
      meta("property", "og:description", page.description);
      meta("property", "og:type", "website");
      meta("property", "og:url", `${origin}${path}`);
      meta("property", "og:image", `${origin}/viddie-icon.png`);
      if (!canonical) {
        canonical = document.createElement("link");
        canonical.rel = "canonical";
        document.head.appendChild(canonical);
      }
      canonical.href = `${origin}${path}`;
    } else {
      canonical?.remove();
      meta("property", "og:url", null);
    }
  }, [pathname]);
  return null;
}
