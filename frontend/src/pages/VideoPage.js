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

  useEffect(() => {
    if (!updated) {
      getVideo(videoId).then((response) => {
        setVideoInfo(response);
      });
    }
  }, []);
  useEffect(() => {
    if (updated) {
      getVideo(videoId).then((response) => {
        setVideoInfo(response);
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

        {videoInfo.scenes.map((scene) => {
          return (
            <Scene
              scene={scene}
              setUpdated={setUpdated}
              video_type={videoInfo.video_type}
            />
          );
        })}
        {videoInfo?.video_type === "TWITCH" ? (
          <button className="bg-white p-2 pr-4 rounded-full shadow-lg hover:bg-gray-200 ">
            <FaPlus
              className="text-orange-500 w-5 h-5"
              onClick={(e) => {
                setShowAddSceneModal(true);
              }}
            />
          </button>
        ) : (
          <button className="bg-white p-2 pr-4 rounded-full shadow-lg hover:bg-gray-200 ">
            <FaPlus
              className="text-orange-500 w-5 h-5"
              onClick={(e) => {
                setShowAddSceneModal(true);
              }}
            />
          </button>
        )}
      </div>
    </>
  );
};
