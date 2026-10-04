import { Link, useParams } from "react-router-dom";
import React, { useCallback, useState, useEffect } from "react";
import { getVideo } from "../api/apiService";
import { IoIosSettings } from "react-icons/io";
import { FaPlus } from "react-icons/fa6";
import { VideoConfigModal } from "../components/VideoConfigModal";
import { Scene } from "../components/Scene";
import { GiProcessor } from "react-icons/gi";
import { RenderModal } from "../components/RenderModal";
import { ResumeModal } from "../components/ResumeModal";
import { FaRedo } from "react-icons/fa";
import { TwitchSceneCreationModal } from "../components/CreateTwitchSceneModal";
import { SceneCreationModal } from "../components/CreateSceneModal";

export const Video = () => {
  const { videoId } = useParams();
  const [videoInfo, setVideoInfo] = useState(null);
  const [refresh, setRefresh] = useState(0);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showRenderModal, setShowRenderModal] = useState(false);
  const [renderPending, setRenderPending] = useState(false);
  const [showAddTwitchSceneModal, setShowAddTwitchSceneModal] = useState(false);
  const [showAddSceneModal, setShowAddSceneModal] = useState(false);
  const [showResumeModal, setShowResumeModal] = useState(false);

  const setUpdated = useCallback(() => setRefresh((count) => count + 1), []);

  useEffect(() => {
    let cancelled = false;

    getVideo(videoId).then(({ data: response }) => {
      if (cancelled) return;
      if (response) setVideoInfo(response);
    });

    return () => {
      cancelled = true;
    };
  }, [videoId, refresh]);

  const isRenderable =
    !renderPending && (videoInfo?.status === "READY" || videoInfo?.status === "COMPLETED");
  const isResumable = videoInfo?.status === "FAILED";
  const missingNarration = videoInfo?.scenes?.filter(scene => scene.narration_status === "missing") || [];

  return (
    <>
      <VideoConfigModal
        showModal={showConfigModal}
        setShowModal={setShowConfigModal}
        onSaved={setUpdated}
        info={{
          title: videoInfo?.title,
          intro: videoInfo?.intro,
          outro: videoInfo?.outro,
          avatar: videoInfo?.avatar,
          video_type: videoInfo?.video_type,
          settings: videoInfo?.settings,
          id: videoInfo?.id,
        }}
      />

      <TwitchSceneCreationModal
        showModal={showAddTwitchSceneModal}
        setShowModal={setShowAddTwitchSceneModal}
        id={videoInfo?.id}
        setItems={setUpdated}
      />

      <SceneCreationModal
        showModal={showAddSceneModal}
        setShowModal={setShowAddSceneModal}
        id={videoInfo?.id}
        setItems={setUpdated}
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
            <button type="button" disabled={!videoInfo} aria-label="Video settings" onClick={() => setShowConfigModal(true)} className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"><IoIosSettings className="h-5 w-5" />Settings</button>
            {isResumable && <button type="button" onClick={() => setShowResumeModal(true)} className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-700"><FaRedo />Carry on</button>}
            <button type="button" disabled={!isRenderable} title={isRenderable ? "Render video" : `Cannot render while ${videoInfo?.status || "loading"}`} onClick={() => setShowRenderModal(true)} className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"><GiProcessor className="h-5 w-5" />{renderPending ? "Starting render…" : videoInfo?.status === "RENDERING" ? "Rendering…" : "Render video"}</button>
          </div>
        </header>
        {missingNarration.length > 0 && <div role="status" className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
          <p className="font-semibold">{missingNarration.length} {missingNarration.length === 1 ? "scene is" : "scenes are"} missing narration</p>
          <p className="mt-1">Your script and visuals are saved. Retry narration in the scenes below, or render with the available audio.</p>
          <div className="mt-3 flex flex-wrap gap-2">{videoInfo.scenes.map((scene, index) => scene.narration_status === "missing" && <a key={scene.id} href={`#scene-${scene.id}`} className="rounded-lg border border-amber-300 px-3 py-1 font-medium hover:bg-amber-100 dark:border-amber-700 dark:hover:bg-amber-900/40">Scene {index + 1}</a>)}</div>
        </div>}
        <div className="grid items-start gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
          <aside className="min-w-0 rounded-2xl border border-gray-200 bg-white p-5 lg:sticky lg:top-6 dark:border-gray-700 dark:bg-gray-800">
            <div className="flex items-center justify-between gap-2"><h2 className="font-semibold text-gray-900 dark:text-white">Your scenes</h2><span className="rounded-lg bg-gray-100 px-2 py-1 text-xs text-gray-500 dark:bg-gray-700 dark:text-gray-300">{videoInfo?.scenes?.length || 0}</span></div>
            <span className={`mt-4 inline-flex rounded-full px-3 py-1 text-xs font-medium ${isRenderable ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300" : isResumable ? "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300" : "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"}`}>{videoInfo?.status?.replaceAll("_", " ").toLowerCase() || "Loading"}</span>
            <nav aria-label="Scene navigation" className="mt-4 flex gap-2 overflow-x-auto lg:max-h-[50vh] lg:flex-col lg:overflow-y-auto">
              {videoInfo?.scenes?.map((scene, index) => <a key={scene.id} href={`#scene-${scene.id}`} className="flex min-w-0 max-w-[220px] shrink-0 items-center gap-3 rounded-lg px-2 py-2 text-sm text-gray-600 hover:bg-blue-50 hover:text-blue-700 dark:text-gray-300 dark:hover:bg-gray-700"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-xs font-semibold dark:bg-gray-700">{index + 1}</span><span className="truncate">{scene.text || `Scene ${index + 1}`}</span></a>)}
            </nav>
            <p className="mt-5 border-t border-gray-100 pt-4 text-xs leading-relaxed text-gray-500 dark:border-gray-700 dark:text-gray-400">Changes to scenes are saved individually. Render again to include them in your final video.</p>
          </aside>
          <section aria-label="Scenes" className="min-w-0 space-y-5">
            {videoInfo?.scenes?.map((scene, index) => <Scene key={scene.id} scene={scene} index={index} setUpdated={setUpdated} video_type={videoInfo.video_type} video_format={videoInfo.settings?.video_format || "LANDSCAPE"} />)}
            {videoInfo && !videoInfo.scenes?.length && <div className="rounded-2xl border border-dashed border-gray-300 p-10 text-center dark:border-gray-600"><h2 className="font-semibold text-gray-900 dark:text-white">Your story starts here</h2><p className="mt-2 text-sm text-gray-500">Add a scene to start building your video.</p></div>}
            <button type="button" disabled={!videoInfo} onClick={() => videoInfo?.video_type === "TWITCH" ? setShowAddTwitchSceneModal(true) : setShowAddSceneModal(true)} className="flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-gray-200 py-5 text-sm font-semibold text-gray-500 transition hover:border-blue-400 hover:bg-blue-50 hover:text-blue-600 disabled:opacity-40 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-800"><FaPlus />Add scene</button>
          </section>
        </div>
      </main>
    </>
  );
};
