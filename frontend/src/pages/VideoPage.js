import { useParams } from "react-router-dom";
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
  const [videoInfo, setVideoInfo] = useState({ title: "re", scenes: [] });
  const [refresh, setRefresh] = useState(0);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showRenderModal, setShowRenderModal] = useState(false);
  const [showAddTwitchSceneModal, setShowAddTwitchSceneModal] = useState(false);
  const [showAddSceneModal, setShowAddSceneModal] = useState(false);
  const [showResumeModal, setShowResumeModal] = useState(false);

  const setUpdated = useCallback(() => setRefresh((count) => count + 1), []);

  useEffect(() => {
    let cancelled = false;

    getVideo(videoId).then((response) => {
      if (cancelled) return;
      if (response) setVideoInfo(response);
    });

    return () => {
      cancelled = true;
    };
  }, [videoId, refresh]);

  const isRenderable =
    videoInfo?.status === "READY" || videoInfo?.status === "COMPLETED";
  const isResumable = videoInfo?.status === "FAILED";

  return (
    <>
      <VideoConfigModal
        showModal={showConfigModal}
        setShowModal={setShowConfigModal}
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
        onFinished={() => setUpdated(true)}
      />

      <ResumeModal
        showModal={showResumeModal}
        setShowModal={setShowResumeModal}
        id={videoId}
        name={videoInfo?.title}
        onFinished={() => setUpdated(true)}
      />

      <div className="flex flex-col items-center">
        <div className="flex items-center gap-2">
          <h1 className="pt-4 pb-4 font-bold">{videoInfo?.title}</h1>
          <button
            type="button"
            disabled={!isRenderable}
            title={
              isRenderable
                ? "Render video"
                : `Cannot render while ${videoInfo?.status}`
            }
            onClick={() => setShowRenderModal(true)}
            className="flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <GiProcessor className="h-4 w-4" />
            Render
          </button>

          {isResumable ? (
            <button
              type="button"
              title="Carry on generating this video"
              onClick={() => setShowResumeModal(true)}
              className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-400"
            >
              <FaRedo className="h-4 w-4" />
              Carry on
            </button>
          ) : null}

          <button
            type="button"
            aria-label="Video settings"
            title="Video settings"
            onClick={() => setShowConfigModal(true)}
            className="rounded-full bg-white/90 p-2 shadow transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-gray-400 dark:bg-gray-900/80 dark:hover:bg-gray-900"
          >
            <IoIosSettings className="h-5 w-5 text-gray-700 dark:text-gray-200" />
          </button>
        </div>

        {videoInfo?.scenes?.map((scene) => {
          return (
            <Scene
              key={scene.id}
              scene={scene}
              setUpdated={setUpdated}
              video_type={videoInfo.video_type}
            />
          );
        })}
        <button
          type="button"
          onClick={() =>
            videoInfo?.video_type === "TWITCH"
              ? setShowAddTwitchSceneModal(true)
              : setShowAddSceneModal(true)
          }
          className="mb-4 flex items-center gap-2 rounded-lg border-2 border-dashed border-gray-300 bg-white/50 px-5 py-2.5 text-sm font-medium text-gray-600 transition hover:border-orange-400 hover:text-orange-600 focus:outline-none focus:ring-2 focus:ring-orange-400 dark:border-gray-600 dark:bg-gray-800/50 dark:text-gray-300 dark:hover:border-orange-400 dark:hover:text-orange-400"
        >
          <FaPlus className="h-4 w-4 text-orange-500" />
          Add scene
        </button>
      </div>
    </>
  );
};
