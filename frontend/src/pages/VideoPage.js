import { useParams } from "react-router-dom";
import React, { useState, useEffect } from "react";
import { getVideo } from "../api/apiService";
import { IoIosSettings } from "react-icons/io";
import { FaPlus } from "react-icons/fa6";
import { VideoConfigModal } from "../components/VideoConfigModal";
import { Scene } from "../components/Scene";
import { GiProcessor } from "react-icons/gi";
import { RenderModal } from "../components/RenderModal";
import { TwitchSceneCreationModal } from "../components/CreateTwitchSceneModal";
import { SceneCreationModal } from "../components/CreateSceneModal";

export const Video = () => {
  const { videoId } = useParams();
  const [videoInfo, setVideoInfo] = useState({ title: "re", scenes: [] });
  const [updated, setUpdated] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showRenderModal, setShowRenderModal] = useState(false);
  const [showAddTwitchSceneModal, setShowAddTwitchSceneModal] = useState(false);
  const [showAddSceneModal, setShowAddSceneModal] = useState(false);

  // getVideo resolves undefined when the request fails, which would blank the state
  // and break the scenes map below, so only adopt a response that came back.
  useEffect(() => {
    if (!updated) {
      getVideo(videoId).then((response) => {
        if (response) setVideoInfo(response);
      });
    }
  }, []);
  useEffect(() => {
    if (updated) {
      getVideo(videoId).then((response) => {
        if (response) setVideoInfo(response);
        setUpdated(false);
      });
    }
  }, [updated]);

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

      <div className="flex flex-col items-center">
        <div className="flex items-center gap-4">
          <h1 className="pt-4 pb-4 font-bold">{videoInfo?.title}</h1>
          <IoIosSettings
            onClick={(e) => {
              setShowConfigModal(true);
            }}
            className="font-black ml-auto w-6 h-6 text-black  hover:text-gray-400"
          />

          <GiProcessor
            className={`w-5 h-5 text-purple-500 hover:text-red-300`}
            onClick={(e) => {
              setShowRenderModal(true);
            }}
          />
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
        {/* Both branches of this used to be identical, so a Twitch video opened the
            AI scene modal and setShowAddTwitchSceneModal was never called anywhere —
            TwitchSceneCreationModal was rendered but unreachable. The click also sat
            on the icon rather than the button, so the padding was dead and the
            keyboard could not activate it. */}
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
