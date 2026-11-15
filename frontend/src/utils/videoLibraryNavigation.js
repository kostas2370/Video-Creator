import { libraryStatuses, libraryTypes, librarySorts } from "./videoLibrary";

export function libraryQuery(value = "") {
  const params = new URLSearchParams(value);
  const choice = (key, options, fallback = "") => options.some(item => item.value === params.get(key)) ? params.get(key) : fallback;
  const page = Number(params.get("page"));
  return { search: params.get("search") || "", status: choice("status", libraryStatuses), creation_mode: choice("creation_mode", libraryTypes),
    is_favorite: params.get("is_favorite") === "true", ordering: choice("ordering", librarySorts, "-updated_at"),
    view: params.get("view") === "list" ? "list" : "grid", page: Number.isSafeInteger(page) && page > 0 ? page : 1 };
}

export function libraryQueryString(query) {
  const params = new URLSearchParams();
  if (query.search) params.set("search", query.search);
  if (query.status) params.set("status", query.status);
  if (query.creation_mode) params.set("creation_mode", query.creation_mode);
  if (query.is_favorite) params.set("is_favorite", "true");
  if (query.ordering !== "-updated_at") params.set("ordering", query.ordering);
  if (query.view === "list") params.set("view", "list");
  if (query.page > 1) params.set("page", String(query.page));
  return params.toString();
}
const storageKey = owner => owner ? `viddie:video-library:v1:${encodeURIComponent(owner)}` : null;
export function readLibraryNavigation(owner) {
  try {
    const record = JSON.parse(sessionStorage.getItem(storageKey(owner)) || "null");
    if (!owner || !record || typeof record.query !== "string") return null;
    return { query: libraryQueryString(libraryQuery(record.query)), scrollY: Number.isFinite(record.scrollY) && record.scrollY > 0 ? record.scrollY : 0 };
  } catch { return null; }
}
export function saveLibraryNavigation(owner, record) {
  if (!owner) return;
  try { sessionStorage.setItem(storageKey(owner), JSON.stringify(record)); } catch { /* Navigation still works when browser storage is unavailable. */ }
}
export function libraryReturnUrl(owner) {
  const record = readLibraryNavigation(owner);
  return `/videos/${record?.query ? `?${record.query}` : ""}`;
}
