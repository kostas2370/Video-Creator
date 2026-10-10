import { formatDuration } from "../utils/timing";
import { Link, useParams } from "react-router-dom";
import React, { useCallback, useState, useEffect, useRef } from "react";
import { getVideo, reorderScenes, updateSceneTransition, updateSceneTiming, getVideoSubtitles } from "../api/apiService";
import { subscribeUpdates } from "../api/subscribeUpdates";
import { IoIosSettings } from "react-icons/io";
import { FaPlus } from "react-icons/fa6";
import { VideoConfigModal } from "../components/VideoConfigModal";
import { ReorderableScenes } from "../components/ReorderableScenes";
import { toast } from "react-toastify";
import { GiProcessor } from "react-icons/gi";
import { RenderModal } from "../components/RenderModal";
import { StoryboardModal } from "../components/StoryboardModal";
import { ResumeModal } from "../components/ResumeModal";
import { FaRedo, FaDownload, FaPlay } from "react-icons/fa";
import { SceneCreationModal } from "../components/CreateSceneModal";
import { VideoPreviewModal } from "../components/VideoPreview";

export const Video = () => {
  const { videoId } = useParams();
  const [videoInfo, setVideoInfo] = useState(null);
  const [updateError, setUpdateError] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showRenderModal, setShowRenderModal] = useState(false);
  const [renderPending, setRenderPending] = useState(false);
  const [showAddSceneModal, setShowAddSceneModal] = useState(false);
  const [showStoryboard, setShowStoryboard] = useState(false);
  const [showResumeModal, setShowResumeModal] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [downloadingSubtitles, setDownloadingSubtitles] = useState(false);

  const [pendingSceneChange, setPendingSceneChange] = useState(null);
  const savingOrder = pendingSceneChange?.type === "order";
  const pendingTransition = pendingSceneChange?.type === "transition" ? pendingSceneChange.sceneId : null;
  const pendingTiming = pendingSceneChange?.type === "timing" ? pendingSceneChange.sceneId : null;
  const sceneChangePending = !!pendingSceneChange;
  const savingSceneChangeRef = useRef(false);

  const setUpdated = useCallback(() => setRefresh((count) => count + 1), []);

  const processing = ["GENERATION", "RENDERING"].includes(videoInfo?.status);

  useEffect(() => subscribeUpdates(`videos/${encodeURIComponent(videoId)}/events/`, {
    load: () => getVideo(videoId, { notifyError: false }),
    onUpdate: response => {
      setUpdateError(false);
      if (!savingSceneChangeRef.current) setVideoInfo(response);
    },
    onError: () => setUpdateError(true),
  }), [videoId, refresh]);

  const onSceneQueued = useCallback(() => {
    setVideoInfo(current => current ? { ...current, status: "GENERATION" } : current);
    setUpdated();
  }, [setUpdated]);

  const isRenderable =
    !sceneChangePending && !renderPending && (videoInfo?.status === "READY" || videoInfo?.status === "COMPLETED");
  const saveSceneChange = async (pending, apply, save, fallbackMessage, replaceVideo = false) => {
    if (savingSceneChangeRef.current || processing || renderPending) return;
    const previous = videoInfo;
    savingSceneChangeRef.current = true;
    setPendingSceneChange(pending);
    setVideoInfo(apply);
    try {
      const response = await save();
      if (!response.ok) throw new Error(response.message || fallbackMessage);
      if (replaceVideo) setVideoInfo(response.data);
      else if (pending.type === "timing") setVideoInfo(current => ({ ...current, scenes: current.scenes.map(scene => scene.id === pending.sceneId ? response.data : scene) }));
    } catch (error) {
      setVideoInfo(previous);
      toast.error(error.message || fallbackMessage);
    } finally {
      savingSceneChangeRef.current = false;
      setPendingSceneChange(null);
      setUpdated();
    }
  };
  const onReorder = ordered => saveSceneChange(
    { type: "order" },
    current => ({ ...current, scenes: ordered.map((scene, index) => ({ ...scene, position: index + 1 })) }),
    () => reorderScenes(videoId, ordered.map(scene => scene.id)),
    "Could not save scene order. Please try again.",
    true,
  );
  const onTransition = (scene, changes) => saveSceneChange(
    { type: "transition", sceneId: scene.id },
    current => ({ ...current, scenes: current.scenes.map(row => row.id === scene.id ? { ...row, ...changes } : row) }),
    () => updateSceneTransition(scene.id, changes),
    "Could not save transition. Please try again.",
  );
  const onTiming = (scene, pause) => saveSceneChange(
    { type: "timing", sceneId: scene.id },
    current => ({ ...current, scenes: current.scenes.map(row => row.id === scene.id ? {
      ...row, pause_after: pause,
      timing: row.timing ? { ...row.timing, duration: row.timing.base_duration + pause } : row.timing,
    } : row) }),
    () => updateSceneTiming(scene.id, { pause_after: pause }),
    "Could not save scene timing. Please try again.",
  );
  const durations = videoInfo?.scenes?.map(scene => scene.timing?.duration) || [];
  const runtime = videoInfo && Number.isFinite(videoInfo.extra_duration) && durations.every(Number.isFinite)
    ? durations.reduce((total, duration) => total + duration, videoInfo.extra_duration) : null;
  const downloadSubtitles = async () => {
    if (downloadingSubtitles) return;
    setDownloadingSubtitles(true);
    try {
      const response = await getVideoSubtitles(videoId);
      if (!response.ok) throw new Error(response.message || "Could not download subtitles.");
      const url = URL.createObjectURL(new Blob([response.data], { type: "application/x-subrip;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = url;
      const name = (videoInfo.title || "video").replace(/[<>:"/\\|?*\r\n]/g, "-").slice(0, 80);
      link.download = `${name}-subtitles.srt`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      toast.error(error.message || "Could not download subtitles.");
    } finally {
      setDownloadingSubtitles(false);
    }
  };
  const canDownloadSubtitles = ["READY", "COMPLETED", "FAILED"].includes(videoInfo?.status)
    && !sceneChangePending && !renderPending && videoInfo?.scenes?.some(scene => scene.narration_status === "available");
  const isResumable = videoInfo?.status === "FAILED";
  const canPreview = ["READY", "COMPLETED", "FAILED"].includes(videoInfo?.status)
    && !sceneChangePending && !renderPending && videoInfo?.scenes?.length > 0;
  const missingNarration = videoInfo?.scenes?.filter(scene => scene.narration_status === "missing") || [];

  return (
    <>
      <VideoPreviewModal open={showPreview} onClose={() => setShowPreview(false)} video={videoInfo} disabled={sceneChangePending || renderPending} />
      <StoryboardModal open={showStoryboard} video={videoInfo} onClose={() => setShowStoryboard(false)} onApproved={() => { setShowStoryboard(false); onSceneQueued(); }} />
      <VideoConfigModal
        showModal={showConfigModal}
        setShowModal={setShowConfigModal}
        onSaved={setUpdated}
        info={{
          title: videoInfo?.title,
          intro: videoInfo?.intro,
          outro: videoInfo?.outro,
          avatar: videoInfo?.avatar,
          settings: videoInfo?.settings,
          id: videoInfo?.id,
        }}
      />

      <SceneCreationModal
        showModal={showAddSceneModal}
        setShowModal={setShowAddSceneModal}
        id={videoInfo?.id}
        setItems={onSceneQueued}
        scenes={videoInfo?.scenes || []}
      />

      <RenderModal
        showModal={showRenderModal}
        setShowModal={setShowRenderModal}
        id={videoId}
        name={videoInfo?.title}
        onPendingChange={setRenderPending}
        onUpdate={changes => setVideoInfo(current =>
          String(current?.id) === String(videoId) ? { ...current, ...changes } : current
        )}
        onFinished={() => setUpdated(true)}
      />

      <ResumeModal
        showModal={showResumeModal}
        setShowModal={setShowResumeModal}
        id={videoId}
        name={videoInfo?.title}
        onFinished={() => setUpdated(true)}
      />

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Link to="/videos/" className="text-sm font-medium text-gray-500 hover:text-blue-600 dark:text-gray-400">← All videos</Link>
        <header className="mb-8 mt-5 flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-400">Video editor</p>
            <h1 className="break-words text-3xl font-bold tracking-tight text-gray-900 dark:text-white">{videoInfo?.title || "Loading video…"}</h1>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Fine-tune your story, scene by scene. Render when everything looks right.</p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <button type="button" disabled={!canPreview} title={canPreview ? "Preview your saved edits" : "Preview is available after processing and saving scenes"} onClick={() => setShowPreview(true)} className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"><FaPlay aria-hidden="true" className="h-3.5 w-3.5" />Preview video</button>
            <button type="button" disabled={!videoInfo || videoInfo.status === "REVIEW"} aria-label="Video settings" onClick={() => setShowConfigModal(true)} className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"><IoIosSettings className="h-5 w-5" />Settings</button>
            {isResumable && <button type="button" onClick={() => setShowResumeModal(true)} className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-700"><FaRedo />Carry on</button>}
            <button type="button" disabled={!isRenderable} title={isRenderable ? "Render video" : `Cannot render while ${videoInfo?.status || "loading"}`} onClick={() => setShowRenderModal(true)} className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"><GiProcessor className="h-5 w-5" />{renderPending ? "Starting render…" : videoInfo?.status === "RENDERING" ? "Rendering…" : "Render video"}</button>
          </div>
        </header>
        {videoInfo?.status === "REVIEW" && <div className="mb-6 rounded-2xl border border-blue-200 bg-blue-50 p-5 dark:border-blue-800 dark:bg-blue-900/20">
          <p className="font-semibold">Your storyboard is ready for review</p>
          <p className="mt-1 text-sm">Review the narration and generated visual prompts before creating media.</p>
          <button type="button" onClick={() => setShowStoryboard(true)} className="mt-3 rounded-xl bg-blue-600 px-4 py-2 font-semibold text-white">Review storyboard</button>
        </div>}
        {processing && <div role="status" className="mb-6 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-200">
          <p className="font-semibold">Processing your video…</p>
          <p className="mt-1">Your changes are processing in the background. This page refreshes automatically; you can leave and come back.</p>
          {updateError && <p className="mt-2">Could not load updates. Reconnecting automatically…</p>}
        </div>}
        {videoInfo?.status === "FAILED" && <p role="alert" className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200">Processing failed. Check the available scenes before trying again.</p>}
        {missingNarration.length > 0 && <div role="status" className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
          <p className="font-semibold">{missingNarration.length} {missingNarration.length === 1 ? "scene is" : "scenes are"} missing narration</p>
          <p className="mt-1">Your script and visuals are saved. Retry narration in the scenes below, or render with the available audio.</p>
          <div className="mt-3 flex flex-wrap gap-2">{videoInfo.scenes.map((scene, index) => scene.narration_status === "missing" && <a key={scene.id} href={`#scene-${scene.id}`} className="rounded-lg border border-amber-300 px-3 py-1 font-medium hover:bg-amber-100 dark:border-amber-700 dark:hover:bg-amber-900/40">Scene {index + 1}</a>)}</div>
        </div>}
        <div className="grid items-start gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
          <aside className="min-w-0 rounded-2xl border border-gray-200 bg-white p-5 lg:sticky lg:top-6 dark:border-gray-700 dark:bg-gray-800">
            <div className="flex items-center justify-between gap-2"><h2 className="font-semibold text-gray-900 dark:text-white">Your scenes</h2><span className="rounded-lg bg-gray-100 px-2 py-1 text-xs text-gray-500 dark:bg-gray-700 dark:text-gray-300">{videoInfo?.scenes?.length || 0}</span></div>
            <span className={`mt-4 inline-flex rounded-full px-3 py-1 text-xs font-medium ${isRenderable ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300" : isResumable ? "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300" : "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"}`}>{videoInfo?.status?.replaceAll("_", " ").toLowerCase() || "Loading"}</span>
            <div className="mt-4 rounded-xl bg-gray-50 p-3 dark:bg-gray-900/40"><p className="text-xs text-gray-500 dark:text-gray-400">Estimated runtime</p><p className="mt-1 text-xl font-semibold text-gray-900 dark:text-gray-100" aria-live="polite">{formatDuration(runtime)}</p><p className="mt-1 text-xs leading-relaxed text-gray-400">Includes pauses, intro and outro. Updates as media becomes available.</p></div>
            <button type="button" disabled={!canDownloadSubtitles || downloadingSubtitles} onClick={downloadSubtitles} className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-gray-200 px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-700"><FaDownload aria-hidden="true" />{downloadingSubtitles ? "Downloading…" : "Download SRT"}</button>
            <p className="mt-2 text-xs leading-relaxed text-gray-400">Current edit, using recorded narration. Phrase timing is estimated.</p>
            <nav aria-label="Scene navigation" className="mt-4 flex gap-2 overflow-x-auto lg:max-h-[50vh] lg:flex-col lg:overflow-y-auto">
              {videoInfo?.scenes?.map((scene, index) => <a key={scene.id} href={`#scene-${scene.id}`} className="flex min-w-0 max-w-[220px] shrink-0 items-center gap-3 rounded-lg px-2 py-2 text-sm text-gray-600 hover:bg-blue-50 hover:text-blue-700 dark:text-gray-300 dark:hover:bg-gray-700"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-xs font-semibold dark:bg-gray-700">{index + 1}</span><span className="truncate">{scene.text || `Scene ${index + 1}`}</span></a>)}
            </nav>
            <p className="mt-5 border-t border-gray-100 pt-4 text-xs leading-relaxed text-gray-500 dark:border-gray-700 dark:text-gray-400">Changes to scenes are saved individually. Render again to include them in your final video.</p>
          </aside>
          <section aria-label="Scenes" className="min-w-0 space-y-5">
            <ReorderableScenes scenes={videoInfo?.scenes || []} disabled={sceneChangePending || renderPending || !["READY", "COMPLETED", "FAILED"].includes(videoInfo?.status)} saving={savingOrder} onReorder={onReorder} onTransition={onTransition} pendingTransition={pendingTransition} onTiming={onTiming} pendingTiming={pendingTiming} transitionSettings={videoInfo?.settings || {}} setUpdated={setUpdated} videoFormat={videoInfo?.settings?.video_format || "LANDSCAPE"} />
            {videoInfo && !videoInfo.scenes?.length && <div className="rounded-2xl border border-dashed border-gray-300 p-10 text-center dark:border-gray-600"><h2 className="font-semibold text-gray-900 dark:text-white">{videoInfo.status === "REVIEW" ? "Your prompts are ready" : "Your story starts here"}</h2><p className="mt-2 text-sm text-gray-500">{videoInfo.status === "REVIEW" ? "Review your storyboard and press Proceed to create these scenes." : "Add a scene to start building your video."}</p></div>}
            <button type="button" disabled={!videoInfo || sceneChangePending || renderPending || processing || videoInfo.status === "REVIEW"} onClick={() => setShowAddSceneModal(true)} className="flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-gray-200 py-5 text-sm font-semibold text-gray-500 transition hover:border-blue-400 hover:bg-blue-50 hover:text-blue-600 disabled:opacity-40 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-800"><FaPlus />{processing ? "Processing…" : "Add scene"}</button>
          </section>
        </div>
      </main>
    </>
  );
};
