import React, { useState } from "react";
import { Menu, MenuButton, MenuItems, MenuItem } from "@headlessui/react";
import { FaPencilAlt } from "react-icons/fa";
import { IoTrashBinSharp } from "react-icons/io5";
import { DeleteModal } from "./DeleteModal";
import { FaPlus } from "react-icons/fa6";
import { HiOutlinePencilSquare, HiOutlineEllipsisVertical } from "react-icons/hi2";
import { deleteImageScene, deleteScene, updateScene } from "../api/apiService";
import { EditSceneModal } from "./EditSceneModal";
import { EditSceneImageModal } from "./EditSceneImageModal";
import { API_HOST } from "../endpoints";
import { toast } from "react-toastify";
const formatFrameClasses = {
  LANDSCAPE: "aspect-video w-full",
  PORTRAIT: "mx-auto h-[min(65vh,420px)] max-w-full aspect-[9/16]",
  SQUARE: "mx-auto aspect-square w-full max-w-[420px]",
};

export const Scene = ({ scene, setUpdated, video_type, video_format = "LANDSCAPE", index = 0 }) => {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showDeleteSceneModal, setShowDeleteSceneModal] = useState(false);

  const [showEditModal, setShowEditModal] = useState(false);
  const [showEditImageModal, setShowEditImageModal] = useState(false);

  const MEDIA_URL = API_HOST;
  const [retryingNarration, setRetryingNarration] = useState(false);
  const retryNarration = async () => {
    if (retryingNarration) return;
    setRetryingNarration(true);
    try {
      const response = await updateScene(scene.id, { text: scene.text });
      if (response.ok) {
        if (response.data?.narration_status === "available") toast.success("Narration is ready");
        else toast.warning("Narration is still unavailable. You can retry later or render with the available audio.");
        setUpdated(true);
      }
    } finally { setRetryingNarration(false); }
  };

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
          prompt: scene.scene_image?.prompt,
          with_audio: scene.scene_image?.with_audio,
          video_format,
        }}
        setUpdate={setUpdated}
      />
      <article id={`scene-${scene.id}`} className="scroll-mt-6 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <header className="flex items-center justify-between border-b border-gray-100 px-5 py-4 dark:border-gray-700">
          <h2 className="flex items-center gap-3 font-semibold text-gray-900 dark:text-white"><span className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-sm text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">{index + 1}</span>Scene {index + 1}</h2>
          {video_type !== "TWITCH" && <button type="button" aria-label="Delete scene" onClick={() => setShowDeleteSceneModal(true)} className="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600"><IoTrashBinSharp className="h-4 w-4" /></button>}
        </header>
        <div className="grid gap-6 p-5 md:grid-cols-2">
          <div className="min-w-0">
            <div className="mb-3 flex items-center justify-between"><h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Dialogue</h3>{video_type !== "TWITCH" && <button type="button" aria-label="Edit scene text" onClick={() => setShowEditModal(true)} className="flex items-center gap-2 rounded-lg px-2 py-1 text-sm font-medium text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-gray-700"><FaPencilAlt className="h-3 w-3" />Edit text</button>}</div>
            <p className="min-h-[120px] whitespace-pre-wrap break-words text-sm leading-7 text-gray-700 dark:text-gray-200">{scene.text || "No dialogue yet."}</p>
            {scene.narration_status === "missing" ? <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-900/20">
              <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">Narration unavailable</p>
              <p className="mt-1 text-xs leading-relaxed text-amber-800 dark:text-amber-300">This scene has no narration audio. Your dialogue and visual are saved.</p>
              <button type="button" disabled={retryingNarration} onClick={retryNarration} className="mt-3 rounded-lg bg-amber-100 px-3 py-2 text-xs font-semibold text-amber-900 hover:bg-amber-200 disabled:opacity-50 dark:bg-amber-900/50 dark:text-amber-200">{retryingNarration ? "Retrying…" : "Retry narration"}</button>
            </div> : scene.narration_status === "disabled" ? <p className="mt-4 text-xs text-gray-400">Narration is off for this video</p> : video_type !== "TWITCH" && (scene.file ? <div className="mt-4 border-t border-gray-100 pt-4 dark:border-gray-700"><p className="mb-2 text-xs text-gray-500 dark:text-gray-400">Preview narration</p><audio aria-label={`Scene ${index + 1} narration`} controls key={scene.file} className="h-10 w-full"><source src={MEDIA_URL + scene.file} /></audio></div> : <p className="mt-4 text-xs text-gray-400">No narration yet</p>)}
          </div>
          <div className="min-w-0">
            <div className="mb-3 flex items-center justify-between"><h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Visual</h3>{video_type !== "TWITCH" && <button type="button" onClick={() => setShowEditImageModal(true)} className="flex items-center gap-2 rounded-lg px-2 py-1 text-sm font-medium text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-gray-700"><HiOutlinePencilSquare className="h-4 w-4" />{scene.scene_image?.file ? "Edit visual" : "Add visual"}</button>}</div>
            <div className={`relative overflow-hidden rounded-xl bg-gray-100 dark:bg-gray-900 ${formatFrameClasses[video_format] || formatFrameClasses.LANDSCAPE}`}>
              {scene.scene_image?.file ? (scene.scene_image.file.includes("mp4") ? <video controls src={MEDIA_URL + scene.scene_image.file} className="h-full w-full bg-black object-cover" /> : <img src={MEDIA_URL + scene.scene_image.file} alt={scene.scene_image.prompt || `Scene ${index + 1} visual`} className="h-full w-full object-cover" />) : <div className="flex h-full w-full items-center justify-center text-sm text-gray-400">No visual yet</div>}
          <Menu as="div" className="absolute top-2 right-2 z-10">
            <MenuButton
              aria-label="Image actions"
              className="rounded-full bg-white/90 p-2 shadow transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-gray-400 dark:bg-gray-900/80 dark:hover:bg-gray-900"
            >
              <HiOutlineEllipsisVertical className="h-5 w-5 text-gray-700 dark:text-gray-200" />
            </MenuButton>
            <MenuItems
              anchor="bottom end"
              className="z-50 mt-1 w-44 rounded-lg border border-gray-200 bg-white py-1 shadow-lg focus:outline-none dark:border-gray-700 dark:bg-gray-800"
            >
              {scene.scene_image?.file ? (
                <>
                  {video_type !== "TWITCH" ? (
                    <MenuItem>
                      <button
                        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-gray-700 data-[focus]:bg-gray-100 dark:text-gray-200 dark:data-[focus]:bg-gray-700"
                        onClick={() => setShowEditImageModal(true)}
                      >
                        <HiOutlinePencilSquare className="h-4 w-4 text-green-500" />
                        Edit image
                      </button>
                    </MenuItem>
                  ) : null}
                  <MenuItem>
                    <button
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-600 data-[focus]:bg-gray-100 dark:data-[focus]:bg-gray-700"
                      onClick={() => setShowDeleteModal(true)}
                    >
                      <IoTrashBinSharp className="h-4 w-4" />
                      Delete image
                    </button>
                  </MenuItem>
                </>
              ) : (
                <MenuItem>
                  <button
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-gray-700 data-[focus]:bg-gray-100 dark:text-gray-200 dark:data-[focus]:bg-gray-700"
                    onClick={() => setShowEditImageModal(true)}
                  >
                    <FaPlus className="h-4 w-4 text-orange-500" />
                    Add image
                  </button>
                </MenuItem>
              )}
            </MenuItems>
          </Menu>
            </div>
            {scene.scene_image?.prompt && <p className="mt-3 line-clamp-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">{scene.scene_image.prompt}</p>}
          </div>
        </div>
      </article>
    </>
  );
};
