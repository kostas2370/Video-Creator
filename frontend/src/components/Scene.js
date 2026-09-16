import { useParams } from "react-router-dom";
import React, { useState, useEffect } from "react";
import { FaPencilAlt } from "react-icons/fa";
import { IoTrashBinSharp } from "react-icons/io5";
import { DeleteModal } from "./DeleteModal";
import { FaPlus } from "react-icons/fa6";
import { HiOutlinePencilSquare } from "react-icons/hi2";
import { deleteImageScene, deleteScene } from "../api/apiService";
import { EditSceneModal } from "./EditSceneModal";
import { EditSceneImageModal } from "./EditSceneImageModal";
import { API_HOST } from "../endpoints";
export const Scene = ({ scene, setUpdated, video_type }) => {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showDeleteSceneModal, setShowDeleteSceneModal] = useState(false);

  const [showEditModal, setShowEditModal] = useState(false);
  const [showEditImageModal, setShowEditImageModal] = useState(false);

  // Same host the API is on, so media loads whichever host the app was opened on.
  const MEDIA_URL = API_HOST;

  return (
    <>
      <DeleteModal
        showModal={showDeleteModal}
        setShowModal={setShowDeleteModal}
        id={scene?.scene_image?.id}
        setItems={setUpdated}
        deleteFunction={deleteImageScene}
        name="image"
        mode="image"
      />

    <DeleteModal
        showModal={showDeleteSceneModal}
        setShowModal={setShowDeleteSceneModal}
        id={scene?.id}
        setItems={setUpdated}
        deleteFunction={deleteScene}
        name="Scene"
        mode="image"
      />

      <EditSceneModal
        showModal={showEditModal}
        setShowModal={setShowEditModal}
        scene_info={{ dialogue: scene.text, id: scene.id }}
        setUpdate={setUpdated}
      />
      <EditSceneImageModal
        showModal={showEditImageModal}
        setShowModal={setShowEditImageModal}
        scene_info={{
          image: MEDIA_URL + scene?.scene_image?.file,
          scene_id: scene.id,
          scene_image_id: scene?.scene_image?.id,
          prompt: scene.scene_image.prompt,
          with_audio: scene.scene_image.with_audio,
        }}
        setUpdate={setUpdated}
      />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 px-4 border">
        <div className="relative">
          {video_type !== "TWITCH" ? (
            <>
              <button
                className="absolute top-2 right-4  p-2 pr-4 rounded-full bg-white hover:bg-gray-200"
                onClick={(e) => {
                  setShowEditModal(true);
                }}
              >
                <FaPencilAlt className="text-blue-500" />
              </button>

              <button
                  onClick={(e) => {
                    setShowDeleteSceneModal(true);
                  }}
                  className="absolute top-12 right-4  p-2 pr-4 rounded-full bg-white hover:bg-gray-200"
                >
                  <IoTrashBinSharp className="text-red-500" />
                </button>

              <audio controls key={scene.file}>
                <source src={MEDIA_URL + scene.file ?? ""} />
              </audio>
            </>
          ) : null}

          <div className="relative w-full">
            <textarea
              className="w-full h-40 resize-none p-2.5 text-sm rounded-lg border bg-gray-50 border-gray-300 text-gray-900 disabled:opacity-100 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
              value={scene.text}
              required=""
              disabled
            />
          </div>
        </div>
        <div className="relative inline-block">
          {scene.scene_image?.file &&
          scene.scene_image?.file.includes("mp4") ? (
            <>
              <video
                controls
                src={MEDIA_URL + scene.scene_image.file}
                className="object-cover h-48 w-full md:w-96"
              ></video>
            </>
          ) : (
            <>
              {scene.scene_image?.file ? (
                <>
                  <img
                    src={MEDIA_URL + scene.scene_image.file}
                    alt="Image Missing"
                    className="object-cover h-48 w-full md:w-96"
                  />
                </>
              ) : (
                <>
                  <img
                    src="https://www.shutterstock.com/image-photo/white-cement-concrete-wall-texture-600nw-1891225786.jpg"
                    alt="Image Missing"
                    className="object-cover h-48 w-full md:w-96"
                  />
                </>
              )}
            </>
          )}

          <div className="absolute top-2 right-2 flex space-x-2 ">
            {scene.scene_image?.file ? (
              <>
                {video_type !== "TWITCH" ? (
                  <button
                    className="bg-white p-2 pr-4 rounded-full shadow-lg hover:bg-gray-200"
                    onClick={(e) => {
                      setShowEditImageModal(true);
                    }}
                  >
                    <HiOutlinePencilSquare className="text-green-500 w-5 h-5" />
                  </button>
                ) : null}
                <button
                  onClick={(e) => {
                    setShowDeleteModal(true);
                  }}
                  className="bg-white p-2 rounded-full shadow-lg hover:bg-gray-200"
                >
                  <IoTrashBinSharp className="text-red-500" />
                </button>
              </>
            ) : (
              <button
                onClick={(e) => {
                  setShowEditImageModal(true);
                }}
                className="bg-white p-2 rounded-full shadow-lg hover:bg-gray-200"
              >
                <FaPlus className="text-orange-500" />
              </button>
            )}
          </div>
        </div>
      </div>
      
    </>
  );
};
