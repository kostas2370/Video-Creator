import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { HiOutlineFilm } from "react-icons/hi2";
import { mediaUrl } from "../utils/media";
import { loadVideoThumbnail, thumbnailRequestKey } from "../utils/videoThumbnails";
import { videoFormats } from "../utils/videoFormats";

const focus = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500";

export function VideoThumbnail({ video, compact, badge, statusLabel }) {
  const container = useRef(null);
  const [visible, setVisible] = useState(false);
  const [failedImages, setFailedImages] = useState([]);
  const [generated, setGenerated] = useState(null);
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

  return <Link ref={container} to={`/videos/${video.id}/`} aria-label={`Open ${video.title || "Untitled video"}${statusLabel ? ` · ${statusLabel}` : ""}`} className={`relative flex shrink-0 items-center justify-center overflow-hidden bg-gradient-to-br from-slate-100 via-blue-50 to-indigo-100 text-blue-300 ${focus} dark:from-gray-800 dark:via-slate-800 dark:to-slate-900 dark:text-slate-600 ${compact ? "h-20 w-28 rounded-xl sm:h-20 sm:w-36" : "aspect-video w-full rounded-t-2xl"}`}>
    <HiOutlineFilm aria-hidden="true" className={compact ? "h-8 w-8" : "h-12 w-12"} />
    {image && <img src={image} loading="lazy" decoding="async" alt="" onError={() => setFailedImages(current => [...current, image])} className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 motion-safe:group-hover:scale-105" />}
    {!compact && badge && <span className="absolute left-3 top-3 rounded-lg bg-white/95 backdrop-blur-sm dark:bg-gray-950/95">{badge}</span>}
    {!compact && <span className="absolute bottom-3 right-3 rounded-md bg-gray-950/65 px-2 py-1 text-[10px] font-medium text-white">{videoFormats.find(format => format.value === video.settings?.video_format)?.ratio || "Video"}</span>}
  </Link>;
}

