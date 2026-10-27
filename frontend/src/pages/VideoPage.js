import { DeferredDialog } from "../components/ui/DeferredDialog";
import { RecentlyDeletedScenes } from "../components/RecentlyDeletedScenes";
import { RememberedDetails } from "../components/ui/RememberedDetails";
import { useEditorSelection } from "../hooks/useEditorSelection";
import { useUndoHistory } from "../hooks/useUndoHistory";
import { rememberedScene, sameSceneOrder } from "../utils/editorWorkspace";
import { EditorDialog } from "../components/ui/EditorDialog";
import { PublishVideo } from "../components/PublishVideo";
import { VideoDetails } from "../components/VideoDetails";
import { VideoNotes } from "../components/VideoNotes";
import { API_HOST } from "../endpoints";
import { videoFormats } from "../utils/videoFormats";
import { Link, useParams } from "react-router-dom";
import React, { lazy, useCallback, useState, useEffect, useRef } from "react";
import { getVideo, reorderScenes, archiveScene, restoreScene, updateSceneTransition, updateSceneTiming, updateSceneMotion, applyAutoMotion, getVideoSubtitles } from "../api/apiService";
import { subscribeUpdates } from "../api/subscribeUpdates";
import { FaPlus } from "react-icons/fa6";
import { ReorderableScenes } from "../components/ReorderableScenes";
import { toast } from "react-toastify";
import { FaDownload } from "react-icons/fa";
import { ExportFailure } from "../components/ExportFailure";
import { VideoToolbar } from "../components/VideoToolbar";
import { MusicAudio } from "../components/MusicAudio";
import { BulkAutoMotion, hasStillImage } from "../components/SceneMotion";

const ManualSceneModal = lazy(() => import("../components/ManualSceneModal").then(module => ({ default: module.ManualSceneModal })));
const SceneCreationModal = lazy(() => import("../components/CreateSceneModal").then(module => ({ default: module.SceneCreationModal })));
const ThumbnailCreator = lazy(() => import("../components/ThumbnailCreator").then(module => ({ default: module.ThumbnailCreator })));
const VideoPreviewModal = lazy(() => import("../components/VideoPreview").then(module => ({ default: module.VideoPreviewModal })));
const StoryboardModal = lazy(() => import("../components/StoryboardModal").then(module => ({ default: module.StoryboardModal })));
const VideoConfigModal = lazy(() => import("../components/VideoConfigModal").then(module => ({ default: module.VideoConfigModal })));
const RenderModal = lazy(() => import("../components/RenderModal").then(module => ({ default: module.RenderModal })));
const ResumeModal = lazy(() => import("../components/ResumeModal").then(module => ({ default: module.ResumeModal })));

export const Video = () => {
  const { videoId } = useParams();
  const [videoInfo, setVideoInfo] = useState(null);
  const [updateError, setUpdateError] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [showDetails, setShowDetails] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showRenderModal, setShowRenderModal] = useState(false);
  const [renderPending, setRenderPending] = useState(false);
  const [showAddSceneModal, setShowAddSceneModal] = useState(false);
  const [showStoryboard, setShowStoryboard] = useState(false);
  const [showResumeModal, setShowResumeModal] = useState(false);
  const [showCover, setShowCover] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [showRenderedVideo, setShowRenderedVideo] = useState(false);
  const [playbackError, setPlaybackError] = useState(false);
  const [downloadingSubtitles, setDownloadingSubtitles] = useState(false);
  const [selectedSceneId, setSelectedSceneId] = useEditorSelection(videoId);

  const [pendingSceneChange, setPendingSceneChange] = useState(null);
  const savingOrder = pendingSceneChange?.type === "order";
  const pendingTransition = pendingSceneChange?.type === "transition" ? pendingSceneChange.sceneId : null;
  const pendingMotion = pendingSceneChange?.type === "motion" ? pendingSceneChange.sceneId : null;
  const pendingTiming = pendingSceneChange?.type === "timing" ? pendingSceneChange.sceneId : null;
  const sceneChangePending = !!pendingSceneChange;
  const savingSceneChangeRef = useRef(false);

  const setUpdated = useCallback(() => setRefresh((count) => count + 1), []);

  const renderedUrl = videoInfo?.output ? (/^https?:\/\//i.test(videoInfo.output) ? videoInfo.output : `${API_HOST}${videoInfo.output}`) : null;
  useEffect(() => setPlaybackError(false), [renderedUrl, showRenderedVideo]);
  useEffect(() => setShowRenderedVideo(false), [videoId]);

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

  const manual = videoInfo?.video_type === "MANUAL";
  const story = videoInfo?.settings?.creation_mode === "STORY";
  const CreationModal = manual ? ManualSceneModal : SceneCreationModal;
  const scenes = videoInfo?.scenes || [];
  const { undoEntry, undoMatches, rememberAction, discardLast, clearHistory } = useUndoHistory(videoId, scenes);
  const focusedScene = rememberedScene(scenes, selectedSceneId);
  const selectScene = id => setSelectedSceneId(id);
  const format = videoFormats.find(item => item.value === videoInfo?.settings?.video_format);
  const statusLabel = renderPending ? "Starting export" : sceneChangePending ? "Saving changes" : ({ REVIEW: "Review storyboard", GENERATION: "Preparing scenes", RENDERING: "Exporting video", READY: "Ready to edit", COMPLETED: "Export available", FAILED: "Needs attention" }[videoInfo?.status] || "Loading project");
  const isRenderable =
    !sceneChangePending && !renderPending && videoInfo?.scenes?.length > 0 && (videoInfo?.status === "READY" || videoInfo?.status === "COMPLETED" || (videoInfo?.status === "FAILED" && !!videoInfo?.render_error?.message));
  const saveSceneChange = async (pending, apply, save, fallbackMessage, replaceVideo = false) => {
    if (savingSceneChangeRef.current || processing || renderPending) return false;
    const previous = videoInfo;
    savingSceneChangeRef.current = true;
    setPendingSceneChange(pending);
    setVideoInfo(apply);
    try {
      const response = await save();
      if (!response.ok) throw new Error(response.message || fallbackMessage);
      if (replaceVideo) setVideoInfo(response.data);
      else if (["timing", "motion"].includes(pending.type)) setVideoInfo(current => ({ ...current, scenes: current.scenes.map(scene => scene.id === pending.sceneId ? response.data : scene) }));
      return true;
    } catch (error) {
      setVideoInfo(previous);
      toast.error(error.message || fallbackMessage);
      return false;
    } finally {
      savingSceneChangeRef.current = false;
      setPendingSceneChange(null);
      setUpdated();
    }
  };
  const onReorder = async ordered => {
    const before = scenes.map(scene => scene.id);
    const after = ordered.map(scene => scene.id);
    if (sameSceneOrder(scenes, after)) return false;
    setSelectedSceneId(focusedScene?.id);
    const ok = await saveSceneChange(
      { type: "order" },
      current => ({ ...current, scenes: ordered.map((scene, index) => ({ ...scene, position: index + 1 })) }),
      () => reorderScenes(videoId, after, before),
      "Could not save scene order. Please try again.", true,
    );
    if (ok) rememberAction({ type: "order", before, after, label: "scene move" });
    return ok;
  };
  const onRemoveScene = async scene => {
    const before = scenes.map(row => row.id);
    const after = before.filter(id => id !== scene.id);
    const index = before.indexOf(scene.id);
    const ok = await saveSceneChange(
      { type: "remove" }, current => current,
      () => archiveScene(scene.id, before), "Could not remove this scene.", true,
    );
    if (ok) {
      rememberAction({ type: "remove", sceneId: scene.id, before, after, label: "scene removal" });
      if (focusedScene?.id === scene.id) setSelectedSceneId(after[Math.min(index, after.length - 1)] || null);
    }
    return { ok };
  };
  const canUndo = undoMatches && !sceneChangePending && !processing && !renderPending && ["READY", "COMPLETED", "FAILED"].includes(videoInfo?.status);
  const undo = async () => {
    if (!canUndo) return;
    const ok = await saveSceneChange(
      { type: "undo" }, current => current,
      () => undoEntry.type === "remove" ? restoreScene(undoEntry.sceneId, undoEntry.before, undoEntry.after) : reorderScenes(videoId, undoEntry.before, undoEntry.after),
      "Could not undo this change. Please refresh and try again.", true,
    );
    if (ok) {
      discardLast(undoEntry);
      if (undoEntry.type === "remove") setSelectedSceneId(undoEntry.sceneId);
      toast.success(`Undid ${undoEntry.label}.`);
    }
  };
  const recoverScene = async sceneId => {
    const ok = await saveSceneChange(
      { type: "restore" }, current => current,
      () => restoreScene(sceneId, undefined, scenes.map(scene => scene.id)),
      "Could not restore this scene. Refresh and try again.", true,
    );
    if (ok) {
      clearHistory();
      setSelectedSceneId(sceneId);
      toast.success("Scene restored.");
    }
    return ok;
  };
  const onTransition = (scene, changes) => saveSceneChange(
    { type: "transition", sceneId: scene.id },
    current => ({ ...current, scenes: current.scenes.map(row => row.id === scene.id ? { ...row, ...changes } : row) }),
    () => updateSceneTransition(scene.id, changes),
    "Could not save transition. Please try again.",
  );
  const onAutoMotion = intensity => saveSceneChange(
    { type: "bulkMotion" },
    current => ({ ...current, scenes: current.scenes.map(scene => hasStillImage(scene) ? { ...scene, motion_style: "AUTO", motion_intensity: intensity } : scene) }),
    () => applyAutoMotion(videoId, intensity),
    "Could not apply Auto motion. Please try again.",
    true,
  );
  const onMotion = (scene, changes) => saveSceneChange(
    { type: "motion", sceneId: scene.id },
    current => ({ ...current, scenes: current.scenes.map(row => row.id === scene.id ? { ...row, ...changes } : row) }),
    () => updateSceneMotion(scene.id, changes),
    "Could not save image motion. Please try again.",
  );
  const onTiming = (scene, changes) => saveSceneChange(
    { type: "timing", sceneId: scene.id },
    current => current,
    () => updateSceneTiming(scene.id, changes),
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
    && !sceneChangePending && !renderPending && videoInfo?.scenes?.some(scene => scene.narration_status === "available" || (manual && scene.text));
  const isResumable = !manual && videoInfo?.status === "FAILED" && !videoInfo?.render_error?.message;
  const canPreview = ["READY", "COMPLETED", "FAILED"].includes(videoInfo?.status)
    && !sceneChangePending && !renderPending && videoInfo?.scenes?.length > 0;
  const missingNarration = videoInfo?.scenes?.filter(scene => scene.narration_status === "missing") || [];

  return (
    <>
      <EditorDialog open={showRenderedVideo && !!renderedUrl} onClose={() => setShowRenderedVideo(false)} title="Watch export" description={videoInfo?.status === "RENDERING" ? "Your previous export is available while the new video renders." : "Watch your latest export. Export again to include any new edits."} maxWidth="max-w-4xl">
        {showRenderedVideo && renderedUrl && <>
          <video key={renderedUrl} src={renderedUrl} controls playsInline preload="metadata" aria-label="Latest rendered video" onError={() => setPlaybackError(true)} onCanPlay={() => setPlaybackError(false)} className="mx-auto max-h-[60vh] w-full rounded-xl bg-black" />
          {playbackError && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-300">Could not play this export. Try opening the video using the link below.</p>}
          <a href={renderedUrl} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex rounded-lg px-3 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-300 dark:hover:bg-gray-700">Open video in new tab ↗</a>
        </>}
      </EditorDialog>
      <DeferredDialog open={showCover} onClose={() => setShowCover(false)}><ThumbnailCreator open={showCover} onClose={() => setShowCover(false)} video={videoInfo} onSaved={changes => setVideoInfo(current => ({ ...current, ...changes }))} /></DeferredDialog>
      <DeferredDialog open={showPreview} onClose={() => setShowPreview(false)}><VideoPreviewModal open={showPreview} onClose={() => setShowPreview(false)} video={videoInfo} disabled={sceneChangePending || renderPending} /></DeferredDialog>
      <DeferredDialog open={showStoryboard} onClose={() => setShowStoryboard(false)}><StoryboardModal open={showStoryboard} video={videoInfo} onClose={() => setShowStoryboard(false)} onApproved={() => { setShowStoryboard(false); onSceneQueued(); }} /></DeferredDialog>
      <DeferredDialog open={showConfigModal} onClose={() => setShowConfigModal(false)}><VideoConfigModal
        showModal={showConfigModal}
        setShowModal={setShowConfigModal}
        onSaved={setUpdated}
        info={{
          title: videoInfo?.title,
          intro: videoInfo?.intro,
          outro: videoInfo?.outro,
          avatar: videoInfo?.avatar,
          voice_model: videoInfo?.voice_model,
          settings: videoInfo?.settings,
          id: videoInfo?.id,
          video_type: videoInfo?.video_type,
        }}
      /></DeferredDialog>

      <DeferredDialog open={showAddSceneModal} onClose={() => setShowAddSceneModal(false)}><CreationModal
        showModal={showAddSceneModal}
        setShowModal={setShowAddSceneModal}
        id={videoInfo?.id}
        setItems={onSceneQueued}
        scenes={videoInfo?.scenes || []}
      /></DeferredDialog>

      <DeferredDialog open={showRenderModal} onClose={() => setShowRenderModal(false)}><RenderModal
        showModal={showRenderModal}
        setShowModal={setShowRenderModal}
        id={videoId}
        name={videoInfo?.title}
        onPendingChange={setRenderPending}
        onUpdate={changes => setVideoInfo(current =>
          String(current?.id) === String(videoId) ? { ...current, ...changes } : current
        )}
        onFinished={() => setUpdated(true)}
      /></DeferredDialog>

      <DeferredDialog open={showResumeModal} onClose={() => setShowResumeModal(false)}><ResumeModal
        showModal={showResumeModal}
        setShowModal={setShowResumeModal}
        id={videoId}
        name={videoInfo?.title}
        onFinished={() => setUpdated(true)}
      /></DeferredDialog>

      <main className="editor-workspace mx-auto max-w-6xl px-4 py-5 sm:px-6">
        <Link to="/videos/" className="text-sm font-medium text-gray-500 hover:text-blue-600 dark:text-gray-400">← All videos</Link>
        <header className="mb-4 mt-3">
          <div className="min-w-0">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-400">{story ? "Story video editor" : manual ? "Manual video editor" : "Video editor"}</p>
            <h1 className="break-words text-xl font-bold sm:text-2xl tracking-tight text-gray-900 dark:text-white">{videoInfo?.title || "Loading video…"}</h1>

          </div>
        </header>
        <ExportFailure video={videoInfo} disabled={!isRenderable} onRetry={() => setShowRenderModal(true)} />
        <VideoToolbar video={videoInfo} sceneCount={scenes.length} runtime={runtime} format={format}
          statusLabel={statusLabel} processing={processing} canPreview={canPreview} canExport={isRenderable}
          renderPending={renderPending} saving={sceneChangePending} isResumable={isResumable}
          onUndo={undo} canUndo={canUndo} undoLabel={undoEntry ? `Undo ${undoEntry.label}` : "Nothing to undo yet"} undoStale={!!undoEntry && !undoMatches}
          onViewRendered={renderedUrl && String(videoInfo?.id) === String(videoId) ? () => setShowRenderedVideo(true) : undefined}
          onPreview={() => setShowPreview(true)} onSettings={() => setShowConfigModal(true)}
          onCover={() => setShowCover(true)} onExport={() => setShowRenderModal(true)} onResume={() => setShowResumeModal(true)}
          tagsAction={videoInfo && String(videoInfo.id) === String(videoId) && <><PublishVideo key={`publish-${videoInfo.id}`} video={videoInfo} onEditDetails={() => setShowDetails(true)} disabled={processing || renderPending || sceneChangePending} /><VideoDetails key={`details-${videoInfo.id}`} video={videoInfo} open={showDetails} onOpenChange={setShowDetails} onSaved={details => setVideoInfo(current => current?.id === videoInfo.id ? { ...current, ...details } : current)} /></>}
        />
        {updateError && !processing && <div role="alert" className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200"><p>{videoInfo ? "Could not refresh your project. Reconnecting…" : "Could not load this project. Check your connection and try again."}</p><button type="button" onClick={setUpdated} className="rounded-lg border border-amber-300 px-3 py-2 font-semibold dark:border-amber-700">Try again</button></div>}
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
          <div className="mt-3 flex flex-wrap gap-2">{videoInfo.scenes.map((scene, index) => scene.narration_status === "missing" && <a key={scene.id} href={`#scene-${scene.id}`} onClick={() => selectScene(scene.id)} className="rounded-lg border border-amber-300 px-3 py-1 font-medium hover:bg-amber-100 dark:border-amber-700 dark:hover:bg-amber-900/40">Scene {index + 1}</a>)}</div>
        </div>}

          <section aria-label="Scenes" className="min-w-0 space-y-5">
            <ReorderableScenes onRemoveScene={onRemoveScene} actions={<button type="button" disabled={!videoInfo || sceneChangePending || renderPending || processing || videoInfo.status === "REVIEW"} onClick={() => setShowAddSceneModal(true)} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-40"><FaPlus aria-hidden="true" />Add scene</button>} selectedSceneId={focusedScene?.id} onSelectScene={selectScene} manual={manual && !story} scenes={videoInfo?.scenes || []} disabled={sceneChangePending || renderPending || !["READY", "COMPLETED", "FAILED"].includes(videoInfo?.status)} saving={savingOrder} onReorder={onReorder} onTransition={onTransition} pendingTransition={pendingTransition} onTiming={onTiming} pendingTiming={pendingTiming} onMotion={onMotion} pendingMotion={pendingMotion} transitionSettings={videoInfo?.settings || {}} setUpdated={setUpdated} videoFormat={videoInfo?.settings?.video_format || "LANDSCAPE"} />
            {videoInfo && !videoInfo.scenes?.length && <div className="rounded-2xl border border-dashed border-gray-300 p-10 text-center dark:border-gray-600"><h2 className="font-semibold text-gray-900 dark:text-white">{videoInfo.status === "REVIEW" ? "Your prompts are ready" : "Your story starts here"}</h2><p className="mt-2 text-sm text-gray-500">{videoInfo.status === "REVIEW" ? "Review your storyboard and press Proceed to create these scenes." : manual ? "Add your photos or video clips. Use Audio to record a voiceover and Music to add a soundtrack." : "Add a scene to start building your video."}</p></div>}
            {!scenes.length && <button type="button" disabled={!videoInfo || sceneChangePending || renderPending || processing || videoInfo.status === "REVIEW"} onClick={() => setShowAddSceneModal(true)} className="flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-gray-200 py-5 text-sm font-semibold text-gray-500 transition hover:border-blue-400 hover:bg-blue-50 hover:text-blue-600 disabled:opacity-40 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-800"><FaPlus />{processing ? "Processing…" : manual ? "Add media or blank scene" : "Add scene"}</button>}
          </section>
          <RememberedDetails videoId={videoId} panel="projectExtras" className="editor-panel mt-5 rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
            <summary className="cursor-pointer text-sm font-semibold">Project extras <span className="ml-2 text-xs font-normal text-gray-500 dark:text-gray-400">Notes, music, subtitles &amp; motion</span></summary>
            <div className="mt-4">
          {videoInfo && String(videoInfo.id) === String(videoId) && <VideoNotes key={`notes-${videoInfo.id}`} videoId={videoInfo.id} notes={videoInfo.notes} onSaved={notes => setVideoInfo(current => current?.id === videoInfo.id ? { ...current, notes } : current)} />}
          </div>
          <section aria-label="Audio and motion" className="mt-4 border-t border-gray-100 pt-4 dark:border-gray-700">
            <h2 className="text-sm font-semibold">Audio &amp; motion</h2>
            <div className="mt-4 grid items-start gap-6 sm:grid-cols-3">
              <MusicAudio video={videoInfo} disabled={sceneChangePending || renderPending || !["READY", "COMPLETED", "FAILED"].includes(videoInfo?.status)} onSaved={setUpdated} />
              <div className="mt-5 border-t border-gray-100 pt-4 dark:border-gray-700"><h2 className="text-sm font-semibold">Subtitle file</h2><p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Download captions and timing from your current edit.</p><button type="button" disabled={!canDownloadSubtitles || downloadingSubtitles} onClick={downloadSubtitles} className="mt-3 inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium disabled:opacity-40 dark:border-gray-600"><FaDownload aria-hidden="true" />{downloadingSubtitles ? "Downloading…" : "Download SRT"}</button></div>
              <div className="mt-5 border-t border-gray-100 pt-4 dark:border-gray-700"><h2 className="mb-3 text-sm font-semibold">Image motion</h2><BulkAutoMotion scenes={scenes} disabled={sceneChangePending || renderPending || !["READY", "COMPLETED", "FAILED"].includes(videoInfo?.status)} saving={pendingSceneChange?.type === "bulkMotion"} onApply={onAutoMotion} /></div>
            </div>
          </section>
          {videoInfo && <RecentlyDeletedScenes key={`deleted-${videoId}`} videoId={videoId} refresh={videoInfo.updated_at} disabled={sceneChangePending || renderPending || !["READY", "COMPLETED", "FAILED"].includes(videoInfo.status)} onRestore={recoverScene} />}
          </RememberedDetails>
      </main>
    </>
  );
};
