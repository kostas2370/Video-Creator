import { DeferredVideo } from "./ui/DeferredVideo";
import { useEffect, useState } from "react";
import { HiOutlineMagnifyingGlass, HiOutlinePlus, HiOutlineMusicalNote, HiOutlineFilm } from "react-icons/hi2";
import { getMediaAssets, createMediaAsset, editMediaAsset, deleteMediaAsset, downloadMediaAsset } from "../api/apiService";
import { API_HOST } from "../endpoints";
import { useDebounce } from "../hooks/useDebounce";
import { EditorDialog, editorInput, editorButton } from "./ui/EditorDialog";

const url = file => /^https?:\/\//i.test(file || "") ? file : `${API_HOST}${file}`;

function AssetEditor({ asset, open, onClose, onSaved }) {
  const [title, setTitle] = useState(""), [tags, setTags] = useState(""), [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  useEffect(() => { if (open) { setTitle(asset?.title || ""); setTags((asset?.tags || []).join(", ")); setFile(null); setError(""); } }, [open, asset]);
  const save = async event => {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError("");
    const values = { title: title.trim(), tags: tags.split(",").map(tag => tag.trim()).filter(Boolean) };
    let response;
    if (asset) response = await editMediaAsset(asset.id, values);
    else { const data = new FormData(); data.append("title", values.title); data.append("tags", JSON.stringify(values.tags)); data.append("file", file); response = await createMediaAsset(data); }
    if (response.ok) { onSaved(); onClose(); } else setError(response.message || "Could not save this library item.");
    setBusy(false);
  };
  return <EditorDialog open={open} onClose={onClose} title={asset ? "Edit media details" : "Add to your media library"} description="Save images, clips, and audio once, then reuse them in your videos." busy={busy} maxWidth="max-w-lg" footer={<div className="flex justify-end gap-2"><button disabled={busy} type="button" onClick={onClose} className="px-4 py-3 text-sm text-gray-500">Cancel</button><button disabled={busy || !title.trim() || (!asset && !file)} type="submit" form="library-asset" className={editorButton}>{busy ? "Saving…" : "Save media"}</button></div>}>
    <form id="library-asset" onSubmit={save}><fieldset disabled={busy} className="space-y-4">
      {!asset && <label className="block text-sm">Media file<input type="file" required accept=".jpg,.jpeg,.png,.webp,.mp4,.mov,.webm,.avi,.m4v,.mp3,.wav,.m4a,.aac,.ogg,.flac" onChange={event => { const next = event.target.files?.[0]; if (next?.size > 100 * 1024 * 1024) { setError("Choose a file up to 100 MB."); event.target.value = ""; setFile(null); return; } setFile(next || null); if (!title.trim() && next) setTitle(next.name.replace(/\.[^.]+$/, "").slice(0, 100)); setError(""); }} className={`${editorInput} mt-2`} /><span className="mt-2 block text-xs text-gray-500">Up to 100 MB · Video and audio up to 15 minutes.</span></label>}
      <label className="block text-sm">Name<input required maxLength={100} value={title} onChange={event => setTitle(event.target.value)} className={`${editorInput} mt-2`} /></label>
      <label className="block text-sm">Tags<input value={tags} onChange={event => setTags(event.target.value)} className={`${editorInput} mt-2`} placeholder="travel, gameplay, background" /><span className="mt-2 block text-xs text-gray-500">Separate tags with commas. Up to 12 tags, 30 characters each.</span></label>
      {error && <p role="alert" className="text-sm text-red-600 dark:text-red-300">{error}</p>}
    </fieldset></form>
  </EditorDialog>;
}

export function MediaLibrary({ kind: fixedKind = "", onSelect, selecting = false }) {
  const [search, setSearch] = useState(""), [kind, setKind] = useState(fixedKind), [page, setPage] = useState(1);
  const [result, setResult] = useState(null), [loading, setLoading] = useState(true), [error, setError] = useState("");
  const [editor, setEditor] = useState(false), [asset, setAsset] = useState(null), [reload, setReload] = useState(0), [removing, setRemoving] = useState(null);
  const [downloading, setDownloading] = useState(null);
  const term = useDebounce(search, 350);
  useEffect(() => {
    let active = true; setLoading(true); setError("");
    getMediaAssets(term, page, kind).then(response => { if (!active) return; if (response.ok) setResult(response.data); else setError(response.message || "Could not load your media."); setLoading(false); });
    return () => { active = false; };
  }, [term, page, kind, reload]);
  const remove = async item => {
    if (!window.confirm(`Remove “${item.title}” from your library? Copies already used in videos stay available.`)) return;
    setRemoving(item.id); const response = await deleteMediaAsset(item.id);
    if (response.ok) { setPage(1); setReload(value => value + 1); } else setError(response.message);
    setRemoving(null);
  };
  const download = async item => {
    if (downloading) return;
    setDownloading(item.id); setError("");
    const response = await downloadMediaAsset(item.id);
    if (response.ok) {
      const href = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      const extension = new URL(item.file, window.location.origin).pathname.split(".").pop();
      link.href = href; link.download = `${item.title.replace(/[<>:"/\\|?*]/g, "-")}.${extension}`;
      link.click(); setTimeout(() => URL.revokeObjectURL(href), 1000);
    } else setError(response.message || "Could not download this asset.");
    setDownloading(null);
  };
  return <div className="min-w-0">
    <AssetEditor open={editor} asset={asset} onClose={() => setEditor(false)} onSaved={() => { setPage(1); setReload(value => value + 1); }} />
    <div className="mb-5 flex flex-wrap gap-3"><div className="relative min-w-0 flex-1 basis-48"><HiOutlineMagnifyingGlass aria-hidden="true" className="absolute left-3 top-3 h-5 w-5 text-gray-400" /><input type="search" aria-label="Search media by name or tag" value={search} onChange={event => { setSearch(event.target.value); setPage(1); }} placeholder="Search names or tags…" className={`${editorInput} pl-10`} /></div>{!fixedKind && <div className="w-full shrink-0 sm:w-40"><select aria-label="Media type" value={kind} onChange={event => { setKind(event.target.value); setPage(1); }} className={editorInput}><option value="">All media</option><option value="IMAGE">Images</option><option value="VIDEO">Video clips</option><option value="AUDIO">Audio</option></select></div>}<button type="button" disabled={selecting} onClick={() => { setAsset(null); setEditor(true); }} className={`${editorButton} inline-flex items-center gap-2`}><HiOutlinePlus aria-hidden="true" />Upload media</button></div>
    {error && <div role="alert" className="mb-4 text-sm text-red-600 dark:text-red-300">{error} <button type="button" onClick={() => setReload(value => value + 1)} className="underline">Retry</button></div>}
    {loading ? <p role="status" className="py-10 text-center text-sm text-gray-500">Loading your media…</p> : result?.results?.length ? <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{result.results.map(item => <article key={item.id} className="min-w-0 overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-gray-600 dark:bg-gray-800">
      <div className="flex aspect-video items-center justify-center overflow-hidden bg-gray-100 dark:bg-gray-900">{item.kind === "IMAGE" ? <img src={url(item.file)} alt={item.title} loading="lazy" decoding="async" className="h-full w-full object-contain" /> : item.kind === "VIDEO" ? <DeferredVideo src={url(item.file)} controls playsInline preload="none" className="h-full w-full" /> : <div className="w-full px-4"><HiOutlineMusicalNote aria-hidden="true" className="mx-auto mb-3 h-7 w-7 text-blue-400" /><audio src={url(item.file)} controls preload="none" className="w-full" /></div>}</div>
      <div className="p-3"><h3 className="truncate text-sm font-semibold" title={item.title}>{item.title}</h3><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{item.kind === "IMAGE" ? "Image" : item.kind === "VIDEO" ? "Video clip" : "Audio"}{item.duration ? ` · ${Math.round(item.duration)}s` : ""}</p><div className="mt-2 flex flex-wrap gap-1">{item.tags.map(tag => <button key={tag} type="button" onClick={() => { setSearch(tag); setPage(1); }} className="max-w-full truncate rounded-full bg-blue-50 px-2 py-1 text-[10px] text-blue-700 dark:bg-blue-900/30 dark:text-blue-200">{tag}</button>)}</div><div className="mt-3 flex flex-wrap items-center gap-2"><button type="button" disabled={selecting || !!removing} onClick={() => onSelect?.(item)} className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">{selecting ? "Adding…" : "Use media"}</button><button type="button" disabled={selecting || !!removing} onClick={() => { setAsset(item); setEditor(true); }} className="rounded-lg px-2 py-2 text-xs text-gray-500 dark:text-gray-300">Edit tags</button><button type="button" disabled={!!downloading} onClick={() => download(item)} className="rounded-lg px-2 py-2 text-xs text-gray-500 dark:text-gray-300">{downloading === item.id ? "Downloading…" : "Download"}</button><button type="button" disabled={selecting || !!removing} onClick={() => remove(item)} className="rounded-lg px-2 py-2 text-xs text-red-600 dark:text-red-300">{removing === item.id ? "Removing…" : "Remove"}</button></div></div>
    </article>)}</div> : !error && <div className="rounded-2xl border border-dashed border-gray-300 p-10 text-center dark:border-gray-600"><HiOutlineFilm aria-hidden="true" className="mx-auto mb-3 h-8 w-8 text-gray-400" /><h3 className="font-semibold">{term ? "No matching media" : "Your reusable media starts here"}</h3><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{term ? "Try another name or tag." : "Generated images, clips, and thumbnails are saved here automatically. You can also upload media and add tags to find it quickly."}</p></div>}
    {result && <div className="mt-5 flex flex-wrap items-center justify-between gap-3 text-xs text-gray-500"><span>{result.count} {result.count === 1 ? "item" : "items"} · Page {page}</span><div className="flex gap-2"><button type="button" disabled={loading || !result.previous} onClick={() => setPage(result.previous)} className="rounded-lg border px-3 py-2 disabled:opacity-30">Previous</button><button type="button" disabled={loading || !result.next} onClick={() => setPage(result.next)} className="rounded-lg border px-3 py-2 disabled:opacity-30">Next</button></div></div>}
  </div>;
}
