import { DeferredDialog } from "./ui/DeferredDialog";
import { lazy, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Menu, MenuButton, MenuItems, MenuItem } from "@headlessui/react";
import {
  HiOutlineStar, HiStar, HiOutlineEllipsisHorizontal, HiOutlineFilm, HiOutlinePlay, HiOutlineArrowRight,
  HiOutlineArrowPath, HiOutlineArrowUpTray, HiOutlineInformationCircle, HiOutlineTrash,
} from "react-icons/hi2";
import { formatDistanceToNow, isValid, parseISO } from "date-fns";
import { API_HOST } from "../endpoints";
import { videoLibraryInfo } from "../utils/videoLibrary";
import { loadVideoThumbnail, thumbnailRequestKey } from "../utils/videoThumbnails";
import { videoFormats } from "../utils/videoFormats";
import { deleteVideo, toggleVideoFavorite } from "../api/apiService";
import { DeleteModal } from "./DeleteModal";

const RenderModal = lazy(() => import("./RenderModal").then(module => ({ default: module.RenderModal })));
const ResumeModal = lazy(() => import("./ResumeModal").then(module => ({ default: module.ResumeModal })));
const VideoInfoModal = lazy(() => import("./VideoInfoModal").then(module => ({ default: module.VideoInfoModal })));

const menuItemClass = "flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm text-gray-700 data-[focus]:bg-gray-100 data-[disabled]:cursor-not-allowed data-[disabled]:opacity-40 dark:text-gray-200 dark:data-[focus]:bg-gray-700";
const focus = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500";

function VideoThumbnail({ video, compact }) {
  const container = useRef(null);
  const [visible, setVisible] = useState(false);
  const [failedImages, setFailedImages] = useState([]);
  const [generated, setGenerated] = useState(null);
  const mediaUrl = value => value && (/^https?:\/\//i.test(value) ? value : `${API_HOST}${value}`);
  const requestKey = thumbnailRequestKey(video);
  const generatedUrl = generated?.key === requestKey ? generated.url : null;
  const storedImages = [video.cover, video.thumbnail, generatedUrl].map(mediaUrl).filter(Boolean);
  const hasStoredThumbnail = storedImages.some(url => !failedImages.includes(url));
  const sceneImage = video.preview_media?.type === "image" ? mediaUrl(video.preview_media.url) : null;
  const image = [...storedImages, sceneImage].find(url => url && !failedImages.includes(url));
  const source = video.output || (video.preview_media?.type === "video" && video.preview_media.url);

  useEffect(() => {
    if (!container.current) return;
    if (typeof IntersectionObserver === "undefined") { setVisible(true); return; }
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { setVisible(true); observer.disconnect(); }
    }, { rootMargin: "150px" });
    observer.observe(container.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!visible || hasStoredThumbnail || !source || video.status === "RENDERING") return;
    let cancelled = false;
    loadVideoThumbnail(video).then(response => {
      if (!cancelled && response.ok) setGenerated({ key: requestKey, url: response.data.thumbnail });
    }).catch(() => { /* Keep the scene image or placeholder when a thumbnail cannot be made. */ });
    return () => { cancelled = true; };
  }, [visible, hasStoredThumbnail, source, video, requestKey]);

  return <Link ref={container} to={`/videos/${video.id}/`} aria-label={`Open ${video.title || "Untitled video"}`} className={`relative flex shrink-0 items-center justify-center overflow-hidden bg-gradient-to-br from-slate-100 via-blue-50 to-indigo-100 text-blue-300 ${focus} dark:from-gray-800 dark:via-slate-800 dark:to-slate-900 dark:text-slate-600 ${compact ? "h-20 w-28 rounded-xl sm:h-20 sm:w-36" : "aspect-video w-full rounded-t-2xl"}`}>
    <HiOutlineFilm aria-hidden="true" className={compact ? "h-8 w-8" : "h-12 w-12"} />
    {image && <img src={image} loading="lazy" decoding="async" alt="" onError={() => setFailedImages(current => [...current, image])} className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 motion-safe:group-hover:scale-105" />}
    {!compact && <span className="absolute bottom-3 right-3 rounded-md bg-gray-950/65 px-2 py-1 text-[10px] font-medium text-white">{videoFormats.find(format => format.value === video.settings?.video_format)?.ratio || "Video"}</span>}
  </Link>;
}

export function DefaultTable({ data, setVideos, view = "grid", onUpdated, favoritesOnly = false }) {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [showRenderModal, setShowRenderModal] = useState(false);
  const [renderPending, setRenderPending] = useState(false);
  const [showResumeModal, setShowResumeModal] = useState(false);
  const [id, setId] = useState("");
  const [videoInfo, setVideoInfo] = useState(null);
  const [savingFavorites, setSavingFavorites] = useState(new Set());
  const pendingFavorites = useRef(new Set());
  const [favoriteError, setFavoriteError] = useState("");
  const toggleFavorite = async video => {
    if (pendingFavorites.current.has(video.id)) return;
    pendingFavorites.current.add(video.id);
    setSavingFavorites(new Set(pendingFavorites.current));
    setFavoriteError("");
    try {
      const { data: response } = await toggleVideoFavorite(video.id);
      if (!response || typeof response.is_favorite !== "boolean") throw new Error();
      if (favoritesOnly && !response.is_favorite) onUpdated?.();
      else setVideos(current => current.map(item => item.id === video.id ? { ...item, is_favorite: response.is_favorite } : item));
    } catch {
      setFavoriteError("Could not update this favorite. Please try again.");
    } finally {
      pendingFavorites.current.delete(video.id);
      setSavingFavorites(new Set(pendingFavorites.current));
    }
  };
  const compact = view === "list";
  const showDetails = video => { setVideoInfo(video); setShowVideoModal(true); };

  return <>
    {favoriteError && <p role="alert" className="mb-4 text-sm text-red-600 dark:text-red-400">{favoriteError}</p>}
    <DeleteModal showModal={showDeleteModal} setShowModal={setShowDeleteModal} id={id} setItems={setVideos} deleteFunction={deleteVideo} name="video" />
    <DeferredDialog open={showRenderModal} onClose={() => setShowRenderModal(false)}><RenderModal showModal={showRenderModal} setShowModal={setShowRenderModal} id={id} setItems={setVideos} name="video" onPendingChange={setRenderPending} onFinished={onUpdated} /></DeferredDialog>
    <DeferredDialog open={showResumeModal} onClose={() => setShowResumeModal(false)}><ResumeModal showModal={showResumeModal} setShowModal={setShowResumeModal} id={id} setItems={setVideos} name="this video" onFinished={onUpdated} /></DeferredDialog>
    <DeferredDialog open={showVideoModal} onClose={() => setShowVideoModal(false)}><VideoInfoModal showModal={showVideoModal} setShowModal={setShowVideoModal} videoInfo={videoInfo} /></DeferredDialog>
    <ul className={compact ? "divide-y divide-gray-100 overflow-hidden rounded-2xl border border-gray-200 bg-white dark:divide-gray-700 dark:border-gray-700 dark:bg-gray-800" : "grid gap-5 sm:grid-cols-2 lg:grid-cols-3"}>
      {data?.map(video => {
        const title = video.title || "Untitled video";
        const info = videoLibraryInfo(video);
        const canExport = !(renderPending && video.id === id) && ["COMPLETED", "READY"].includes(video.status);
        const updated = video.updated_at && parseISO(video.updated_at);
        return <li key={video.id} className={`group min-w-0 ${compact ? "flex flex-wrap items-center gap-4 p-4 transition-colors hover:bg-gray-50 dark:hover:bg-gray-900/20" : "flex flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white transition-shadow hover:shadow-lg hover:shadow-gray-900/5 dark:border-gray-700 dark:bg-gray-800"}`}>
          <VideoThumbnail video={video} compact={compact} />
          <div className={compact ? "min-w-0 flex-1" : "flex flex-1 flex-col p-4"}>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs text-gray-500 dark:text-gray-400">{info.mode}</span>
              <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[10px] font-semibold ${info.color}`}>{info.processing && <HiOutlineArrowPath aria-hidden="true" className="h-3 w-3 motion-safe:animate-spin" />}{info.label}</span>
            </div>
            <h2 className="text-sm font-semibold leading-6 text-gray-900 dark:text-white"><Link to={`/videos/${video.id}/`} className={`line-clamp-2 rounded hover:text-blue-600 dark:hover:text-blue-300 ${focus}`}>{title}</Link></h2>
            {updated && isValid(updated) && <p className="mt-1.5 text-[11px] text-gray-400 dark:text-gray-500">Updated <time dateTime={video.updated_at} title={updated.toLocaleString()}>{formatDistanceToNow(updated, { addSuffix: true })}</time></p>}
            <div className={`flex flex-wrap items-center gap-2 ${compact ? "mt-3" : "mt-auto pt-4"}`}>
              <Link to={`/videos/${video.id}/`} aria-label={`Open editor for ${title}`} className={`inline-flex min-h-9 items-center gap-1.5 rounded-lg bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-700 transition-colors hover:bg-blue-50 hover:text-blue-700 dark:bg-gray-700/60 dark:text-gray-200 dark:hover:bg-blue-500/15 dark:hover:text-blue-300 ${focus}`}>{video.status === "REVIEW" ? "Review script" : "Open editor"}<HiOutlineArrowRight aria-hidden="true" className="h-3.5 w-3.5" /></Link>
              {video.status === "COMPLETED" && video.output && <button type="button" aria-label={`Watch ${title}`} onClick={() => showDetails(video)} className={`inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2 py-2 text-xs font-semibold text-blue-600 hover:bg-blue-50 dark:text-blue-300 dark:hover:bg-blue-500/10 ${focus}`}><HiOutlinePlay aria-hidden="true" className="h-3.5 w-3.5" />Watch</button>}
              <button type="button" aria-label={`${video.is_favorite ? "Remove" : "Add"} ${title} ${video.is_favorite ? "from" : "to"} favorites`} aria-pressed={!!video.is_favorite} disabled={savingFavorites.has(video.id)} onClick={() => toggleFavorite(video)} className={`ml-auto rounded-lg p-2 transition disabled:opacity-40 hover:bg-amber-50 dark:hover:bg-amber-500/10 ${video.is_favorite ? "text-amber-500" : "text-gray-400 hover:text-amber-500"} ${focus}`}>{video.is_favorite ? <HiStar aria-hidden="true" className="h-5 w-5" /> : <HiOutlineStar aria-hidden="true" className="h-5 w-5" />}</button>
              <Menu as="div" className="relative">
                <MenuButton aria-label={`Actions for ${title}`} className={`rounded-lg p-2 text-gray-400 transition hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-700 dark:hover:text-white ${focus}`}><HiOutlineEllipsisHorizontal aria-hidden="true" className="h-5 w-5" /></MenuButton>
                <MenuItems anchor="bottom end" className="z-50 mt-1 w-52 rounded-xl border border-gray-200 bg-white p-1 shadow-xl focus:outline-none dark:border-gray-700 dark:bg-gray-800">
                  <MenuItem><button className={menuItemClass} onClick={() => showDetails(video)}><HiOutlineInformationCircle aria-hidden="true" className="h-4 w-4" />Video details</button></MenuItem>
                  <MenuItem disabled={!canExport}><button disabled={!canExport} className={menuItemClass} title={canExport ? "Export this video" : "Open the editor to check processing status"} onClick={() => { setId(video.id); setShowRenderModal(true); }}><HiOutlineArrowUpTray aria-hidden="true" className="h-4 w-4" />Export video</button></MenuItem>
                  {info.canResume && <MenuItem><button className={menuItemClass} onClick={() => { setId(video.id); setShowResumeModal(true); }}><HiOutlineArrowPath aria-hidden="true" className="h-4 w-4" />Retry generation</button></MenuItem>}
                  <div className="my-1 border-t border-gray-100 dark:border-gray-700" />
                  <MenuItem disabled={!info.canDelete}><button disabled={!info.canDelete} className={`${menuItemClass} text-red-600 dark:text-red-400`} title={info.canDelete ? "Delete this video" : "Wait for processing to finish"} onClick={() => { setId(video.id); setShowDeleteModal(true); }}><HiOutlineTrash aria-hidden="true" className="h-4 w-4" />Delete video</button></MenuItem>
                </MenuItems>
              </Menu>
            </div>
          </div>
        </li>;
      })}
    </ul>
  </>;
}
