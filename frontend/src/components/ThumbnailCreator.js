import { useEffect, useRef, useState } from "react";
import { EditorDialog, editorInput, editorButton } from "./ui/EditorDialog";
import { FontPicker } from "./FontPicker";
import { generateVideoCover, getVideoCoverJob, previewVideoCover, saveVideoCover, downloadVideoCover } from "../api/apiService";
import { useObjectUrl } from "../hooks/useObjectUrl";
import { loadVideoThumbnail } from "../utils/videoThumbnails";
import { API_HOST } from "../endpoints";

const mediaUrl = path => /^https?:\/\//i.test(path || "") ? path : `${API_HOST}${path}`;

export function ThumbnailCreator({ open, onClose, video, onSaved }) {
  const [thumbnail, setThumbnail] = useState(null);
  const [failedImages, setFailedImages] = useState([]);
  const [choices, setChoices] = useState({});
  const [preview, setPreview] = useState(null);
  const [previewKey, setPreviewKey] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [duration, setDuration] = useState(0);
  const [sourceImage, setSourceImage] = useState(null);
  const [prompt, setPrompt] = useState("");
  const [job, setJob] = useState(null);
  const generating = !!job;
  const locked = !!busy || generating;
  const player = useRef(null);
  const sequence = useRef(0);
  const previewUrl = useObjectUrl(preview);
  const sourceUrl = useObjectUrl(sourceImage);
  const key = JSON.stringify(choices);
  const currentPreview = !!preview && previewKey === key;
  const savedImages = [video?.cover, video?.thumbnail, thumbnail, video?.preview_media?.type === "image" ? video.preview_media.url : null].filter(Boolean).map(mediaUrl);
  const savedImage = savedImages.find(url => !failedImages.includes(url));
  const displayedImage = previewUrl || sourceUrl || savedImage;
  useEffect(() => {
    setThumbnail(null); setFailedImages([]);
  }, [open, video?.id]);
  useEffect(() => {
    if (!open || savedImage || !video?.output || video.status === "RENDERING") return;
    let cancelled = false;
    loadVideoThumbnail(video).then(response => {
      if (!cancelled && response.ok) setThumbnail(response.data.thumbnail);
    }).catch(() => { /* The empty preview remains available. */ });
    return () => { cancelled = true; };
  }, [open, savedImage, video]);
  useEffect(() => {
    sequence.current += 1;
    if (!open) return;
    setChoices({ time: 0, title: video?.title || "", font: "Poppins", color: "#ffffff", position: "bottom", size: 8, background: true, ...video?.cover_settings, source: "ai" });
    setPreview(null); setPreviewKey(""); setError(""); setSourceImage(null);
    setPrompt(""); setDuration(0); setBusy("");
    try {
      const pending = JSON.parse(localStorage.getItem(`cover-job:${video.id}`) || "null");
      setJob(pending);
      if (pending) { setChoices(pending.choices); setPrompt(pending.prompt || ""); }
    } catch { setJob(null); }
  }, [open, video?.id]);
  useEffect(() => {
    if (!open || !job) return;
    let cancelled = false;
    let timer;
    const finish = (clear = true) => {
      try { if (clear) localStorage.removeItem(`cover-job:${video.id}`); } catch { /* Storage may be unavailable. */ }
      setJob(null);
    };
    const poll = async () => {
      const response = await getVideoCoverJob(video.id, job.id);
      if (cancelled) return;
      if (!response.ok) {
        setError(response.message || "Could not check the thumbnail. Reopen this editor to retry.");
        if (response.status === 404) finish();
        return;
      }
      if (response.data.status === "FAILED") {
        setError(response.data.error); finish(); return;
      }
      if (response.data.status === "SUCCEEDED") {
        const image = await getVideoCoverJob(video.id, job.id, true);
        if (cancelled) return;
        if (!image.ok) {
          setError(image.message || "Could not load the thumbnail. Reopen this editor to retry.");
          return;
        }
        setSourceImage(image.data); setPreview(image.data);
        setPreviewKey(JSON.stringify(job.choices)); finish(false);
        return;
      }
      timer = setTimeout(poll, 2000);
    };
    poll();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [open, job, video?.id]);
  const change = (field, value) => { setChoices(current => ({ ...current, [field]: value })); setError(""); };
  const payload = () => {
    if (choices.source === "frame") return choices;
    const data = new FormData();
    Object.entries(choices).forEach(([field, value]) => data.append(field, String(value)));
    if (sourceImage) data.append("image", sourceImage, "thumbnail.png");
    return data;
  };
  const generate = async () => {
    if (busy || generating) return;
    const token = ++sequence.current;
    setBusy("queue"); setError("");
    const response = await generateVideoCover(video.id, { prompt, title: choices.title || "", time: choices.time || 0 });
    if (token !== sequence.current) return;
    if (response.ok) {
      const pending = { id: response.data.id, choices: { ...choices }, prompt };
      try { localStorage.setItem(`cover-job:${video.id}`, JSON.stringify(pending)); } catch { /* Keep following in memory. */ }
      setJob(pending);
    } else setError(response.message || "Could not queue a thumbnail. Try again.");
    setBusy("");
  };
  const upload = event => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { setError("Choose an image smaller than 10 MB."); return; }
    setSourceImage(file); setPreview(null); setPreviewKey(""); setError("");
  };
  const makePreview = async () => {
    if (busy) return;
    const token = ++sequence.current;
    setBusy("preview"); setError("");
    const response = await previewVideoCover(video.id, payload());
    if (token !== sequence.current) return;
    if (response.ok) { setPreview(response.data); setPreviewKey(key); }
    else setError(response.message || "Could not preview this frame.");
    setBusy("");
  };
  const save = async () => {
    if (busy || !currentPreview) return;
    setBusy("save"); setError("");
    const response = await saveVideoCover(video.id, payload());
    if (response.ok) { try { localStorage.removeItem(`cover-job:${video.id}`); } catch { /* Storage may be unavailable. */ } onSaved(response.data); onClose(); } else setError(response.message || "Could not save the cover.");
    setBusy("");
  };
  const download = async () => {
    setBusy("download"); setError("");
    const response = await downloadVideoCover(video.id);
    if (response.ok) {
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a"); link.href = url; link.download = `${(video.title || "video").replace(/[<>:"/\\|?*]/g, "-")}-cover.png`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } else setError(response.message);
    setBusy("");
  };
  return <EditorDialog open={open} onClose={onClose} title="Create a video cover" description="Generate an AI thumbnail, choose a video frame, or upload your own image. Preview it with a title before saving." busy={!!busy} maxWidth="max-w-5xl" footer={<div className="flex flex-wrap justify-end gap-2">{video?.cover && <button type="button" disabled={locked} onClick={download} className="rounded-xl border border-gray-200 px-4 py-3 text-sm dark:border-gray-600">Download cover</button>}<button type="button" disabled={!!busy} onClick={onClose} className="px-4 py-3 text-sm text-gray-500">{generating ? "Close" : "Cancel"}</button><button type="button" disabled={locked || !currentPreview} onClick={save} className={editorButton}>{busy === "save" ? "Saving…" : "Save cover"}</button></div>}>
    <div className="grid items-start gap-6 md:grid-cols-2">
      <div className="min-w-0 space-y-4">
        <fieldset disabled={locked}><legend className="mb-2 text-sm font-semibold">Choose an image source</legend><div className="grid grid-cols-1 gap-2 sm:grid-cols-3">{[
          ["ai", "AI thumbnail", "Create with AI"], ["frame", "Video frame", video?.output ? "Pick a moment" : "Export video first"], ["upload", "Upload image", "Use your own"],
        ].map(([value, label, hint]) => <label key={value} className={`flex items-center justify-between gap-3 sm:block cursor-pointer rounded-xl border p-3 transition focus-within:ring-2 focus-within:ring-blue-500 ${choices.source === value ? "border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-200" : "border-gray-200 dark:border-gray-600"} ${value === "frame" && !video?.output ? "cursor-not-allowed opacity-40" : ""}`}><input type="radio" name="cover-source" value={value} checked={choices.source === value} disabled={value === "frame" && !video?.output} onChange={() => { change("source", value); setSourceImage(null); setPreview(null); setPreviewKey(""); }} className="sr-only" /><span className="block text-sm font-semibold">{label}</span><span className="mt-1 block text-xs opacity-70">{hint}</span></label>)}</div></fieldset>
        {choices.source === "ai" && <div className="space-y-3"><label className="block text-sm">Visual direction (optional)<textarea rows={3} maxLength={1500} value={prompt} disabled={locked} onChange={event => setPrompt(event.target.value)} placeholder="For example: a dramatic close-up, warm lighting, a simple background" className={`${editorInput} mt-2`} /></label><button type="button" disabled={locked} onClick={generate} className={editorButton}>{generating ? "Generating thumbnail…" : sourceImage ? "Regenerate image" : "Generate AI thumbnail"}</button><p className="text-xs leading-relaxed text-gray-500">Uses your video’s content and an available visual reference. The AI includes your title in the artwork. Each generation uses your OpenAI image credits; changing the title requires regeneration.</p></div>}
        {choices.source === "upload" && <label className="block text-sm">Choose an image<input type="file" accept="image/png,image/jpeg,image/webp" disabled={locked} onChange={upload} className={`${editorInput} mt-2`} /><span className="mt-1 block text-xs text-gray-500">PNG, JPEG, or WebP · up to 10 MB</span></label>}
        {choices.source === "frame" && <><div><h3 className="mb-2 text-sm font-semibold">Choose your frame</h3>{video?.output && <video ref={player} src={mediaUrl(video.output)} controls preload="metadata" onLoadedMetadata={event => setDuration(event.currentTarget.duration)} className="max-h-64 w-full rounded-xl bg-black" />}<button type="button" disabled={locked} onClick={() => { const time = player.current?.currentTime || 0; player.current?.pause(); change("time", Math.round(time * 100) / 100); }} className="mt-2 rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-blue-600 disabled:opacity-40 dark:border-gray-600 dark:text-blue-300">Use current frame</button></div>
        <label className="block text-sm">Frame time (seconds)<input type="number" min={0} max={duration ? Math.max(0, duration - .05) : 86400} step={.1} value={choices.time ?? 0} disabled={locked} onChange={event => { const time = Number(event.target.value); change("time", time); if (player.current && Number.isFinite(time) && time >= 0 && time < player.current.duration) player.current.currentTime = time; }} className={`${editorInput} mt-2`} /></label></>}

      </div>
      <div className="min-w-0 space-y-4 md:sticky md:top-0">
        <section aria-label="Cover preview" className="overflow-hidden rounded-2xl border border-gray-200 dark:border-gray-600">
          <div className="flex flex-wrap items-center justify-between gap-2 bg-gray-50 px-4 py-3 dark:bg-gray-900/40"><h3 className="text-sm font-semibold">Cover preview</h3><span aria-live="polite" className="text-xs text-gray-500 dark:text-gray-400">{generating ? "Generating…" : currentPreview ? "Ready to save" : preview || sourceUrl ? "Unsaved changes" : video?.cover && savedImage === mediaUrl(video.cover) ? "Saved cover" : savedImage ? "Current thumbnail" : "No cover yet"}</span></div>
          <div className="flex min-h-48 items-center justify-center bg-gray-100 p-3 dark:bg-gray-950/50">{displayedImage ? <img src={displayedImage} alt="Video cover preview" onError={() => { if (!previewUrl && !sourceUrl) setFailedImages(current => [...current, displayedImage]); }} className="max-h-80 w-full rounded-lg object-contain" /> : <p className="max-w-xs px-4 py-8 text-center text-sm text-gray-500">{choices.source === "frame" ? "Choose a moment in your video, then preview your cover." : "Generate or upload an image to create your cover."}</p>}</div>
          <p className="px-4 py-3 text-xs leading-relaxed text-gray-500 dark:text-gray-400">{currentPreview ? "This is the image that will be saved as your cover." : preview ? choices.source === "ai" ? "Your title has changed. Regenerate the image before saving." : "Your settings have changed. Update the preview before saving." : sourceUrl ? "Preview your image with its title before saving." : savedImage ? "Your current image stays saved while you create a new cover." : "Your cover helps viewers recognize your video."}</p>
        </section>
      <fieldset disabled={locked} className="min-w-0 space-y-4">
        <label className="block text-sm">Cover title<textarea maxLength={100} rows={3} value={choices.title || ""} onChange={event => change("title", event.target.value)} className={`${editorInput} mt-2`} placeholder="Leave blank for a frame-only cover" /></label>
        {choices.source !== "ai" && <><FontPicker value={choices.font || "Poppins"} onChange={font => change("font", font)} />
        <div className="grid grid-cols-2 gap-3"><label className="text-sm">Placement<select value={choices.position || "bottom"} onChange={event => change("position", event.target.value)} className={`${editorInput} mt-2`}><option value="top">Top</option><option value="middle">Center</option><option value="bottom">Bottom</option></select></label><label className="text-sm">Text color<input type="color" value={choices.color || "#ffffff"} onChange={event => change("color", event.target.value)} className="mt-2 block h-10 w-full" /></label></div>
        <label className="block text-sm">Title size · {choices.size || 8}%<input type="range" min={3} max={16} value={choices.size || 8} onChange={event => change("size", Number(event.target.value))} className="mt-2 w-full accent-blue-600" /></label>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={choices.background ?? true} onChange={event => change("background", event.target.checked)} />Dark background behind the title</label>
        <button type="button" disabled={choices.source !== "frame" && !sourceImage} onClick={makePreview} className={editorButton}>{busy === "preview" ? "Creating preview…" : "Preview cover"}</button>
        <p className="text-xs leading-relaxed text-gray-500">Long titles shrink to fit. Your saved cover uses the image and title shown in the current preview.</p></>}
        {choices.source === "ai" && <p className="text-sm leading-relaxed text-gray-500">The AI designs the title’s font, placement, and colors as part of the image. Leave the title blank for an image without text. Check the lettering before saving.</p>}
      </fieldset>
      </div>
    </div>
    {generating && <p role="status" className="mt-4 text-sm text-blue-600 dark:text-blue-300">Your thumbnail is generating in the background and will be saved to your Media Library. You can close this editor and return to Cover to view it.</p>}
    {error && <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-300">{error}</p>}
  </EditorDialog>;
}
