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
      <div className="mb-4 grid grid-cols-1 gap-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm md:grid-cols-2 dark:border-gray-700 dark:bg-gray-800">
        <div className="relative">
          {video_type !== "TWITCH" ? (
            <>
              <div className="absolute right-0 top-0 z-10 flex gap-2">
                <button
                  type="button"
                  aria-label="Edit scene text"
                  className="rounded-full bg-white/90 p-2 shadow hover:bg-white dark:bg-gray-900/80 dark:hover:bg-gray-900"
                  onClick={() => setShowEditModal(true)}
                >
                  <FaPencilAlt className="h-4 w-4 text-blue-500" />
                </button>
                <button
                  type="button"
                  aria-label="Delete scene"
                  className="rounded-full bg-white/90 p-2 shadow hover:bg-white dark:bg-gray-900/80 dark:hover:bg-gray-900"
                  onClick={() => setShowDeleteSceneModal(true)}
                >
                  <IoTrashBinSharp className="h-4 w-4 text-red-500" />
                </button>
              </div>

              <audio controls key={scene.file} className="mb-3 w-full">
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
                className="h-48 w-full rounded-lg object-cover"
              ></video>
            </>
          ) : (
            <>
              {scene.scene_image?.file ? (
                <img
                  src={MEDIA_URL + scene.scene_image.file}
                  alt={scene.scene_image.prompt || "Scene image"}
                  className="h-48 w-full rounded-lg object-cover"
                />
              ) : (
                /* Was a watermarked stock photo fetched from shutterstock.com just to
                   fill the gap — an external request, and it read as a real image. */
                <div className="flex h-48 w-full items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-400">
                  No image yet
                </div>
              )}
            </>
          )}

          <div className="absolute top-2 right-2 flex space-x-2 ">
            {scene.scene_image?.file ? (
              <>
                {video_type !== "TWITCH" ? (
                  <button
                    className="rounded-full bg-white/90 p-2 shadow hover:bg-white dark:bg-gray-900/80 dark:hover:bg-gray-900"
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
                  className="rounded-full bg-white/90 p-2 shadow hover:bg-white dark:bg-gray-900/80 dark:hover:bg-gray-900"
                >
                  <IoTrashBinSharp className="text-red-500" />
                </button>
              </>
            ) : (
              <button
                onClick={(e) => {
                  setShowEditImageModal(true);
                }}
                className="rounded-full bg-white/90 p-2 shadow hover:bg-white dark:bg-gray-900/80 dark:hover:bg-gray-900"
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
