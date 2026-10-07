
import { useState } from "react";
import { Menu, MenuButton, MenuItems, MenuItem } from "@headlessui/react";
import { HiOutlineEllipsisVertical, HiOutlineFilm } from "react-icons/hi2";
import { FaRegEye, FaPencilAlt, FaRedo } from "react-icons/fa";
import { RiDeleteBin6Fill } from "react-icons/ri";
import { DeleteModal } from "./DeleteModal";
import { deleteVideo } from "../api/apiService";
import { VideoInfoModal } from "./VideoInfoModal";
import { GiProcessor } from "react-icons/gi";
import { RenderModal } from "./RenderModal";
import { ResumeModal } from "./ResumeModal";
import { useNavigate } from "react-router-dom";


const menuItemClass =
  "flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-gray-700 data-[focus]:bg-gray-100 data-[disabled]:cursor-not-allowed data-[disabled]:opacity-40 dark:text-gray-200 dark:data-[focus]:bg-gray-700";

export function DefaultTable({ data, setVideos }) {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [showRenderModal, setShowRenderModal] = useState(false);
  const [renderPending, setRenderPending] = useState(false);
  const [showResumeModal, setShowResumeModal] = useState(false);
  const navigate = useNavigate();

  const [id, setId] = useState("");
  const selectedId = id;
  const [videoInfo, setVideoInfo] = useState(null);

  return (
    <>
      <DeleteModal
        showModal={showDeleteModal}
        setShowModal={setShowDeleteModal}
        id={id}
        setItems={setVideos}
        deleteFunction={deleteVideo}
        name="video"
      />

      <RenderModal
        showModal={showRenderModal}
        setShowModal={setShowRenderModal}
        id={id}
        setItems={setVideos}
        name="video"
        onPendingChange={setRenderPending}
      />

      <ResumeModal
        showModal={showResumeModal}
        setShowModal={setShowResumeModal}
        id={id}
        setItems={setVideos}
        name="this video"
      />

      <VideoInfoModal
        showModal={showVideoModal}
        setShowModal={setShowVideoModal}
        videoInfo={videoInfo}
      />

      <ul className="divide-y divide-gray-100 dark:divide-gray-700">
        {data?.map(({ title, status, output, id, prompt, music, gpt_answer }) => {
          const isCompleted = status === "COMPLETED";
          const isRenderable = !(renderPending && id === selectedId) && (isCompleted || status === "READY");
          const isEditable = isRenderable;
          const isDeletable = status !== "RENDERING";
          const isResumable = status === "FAILED";
          const statusColor = isCompleted ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300" : status === "FAILED" ? "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300" : status === "READY" ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" : "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
          return <li key={id} className="flex flex-col gap-4 p-5 transition hover:bg-gray-50/80 sm:flex-row sm:items-center dark:hover:bg-gray-900/20">
            <div className="flex min-w-0 flex-1 items-center gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-gray-100 text-gray-400 dark:bg-gray-700"><HiOutlineFilm className="h-6 w-6" /></div>
              <div className="min-w-0"><h3 className="break-words text-sm font-semibold text-gray-900 dark:text-white">{title || "Untitled video"}</h3><div className="mt-2 flex flex-wrap items-center gap-2"><span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusColor}`}>{status?.replaceAll("_", " ").toLowerCase()}</span><span className="text-xs text-gray-400">Generated video</span></div></div>
            </div>
            <div className="flex shrink-0 items-center justify-end gap-2">
              {isEditable && <button type="button" aria-label={`Edit ${title}`} onClick={() => navigate(`/videos/${id}/`)} className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium text-gray-600 hover:border-blue-300 hover:text-blue-600 dark:border-gray-600 dark:text-gray-300"><FaPencilAlt />Edit scenes</button>}
              {isCompleted && output && <button type="button" aria-label={`Watch ${title}`} onClick={() => { setVideoInfo({title,prompt,gpt_answer,music,output}); setShowVideoModal(true); }} className="flex items-center gap-2 rounded-lg bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-600 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300"><FaRegEye />Watch</button>}
                      <Menu as="div" className="relative inline-block text-left">
                        <MenuButton
                          aria-label={`Actions for ${title}`}
                          className="rounded-full p-2 transition hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-400 dark:hover:bg-gray-700"
                        >
                          <HiOutlineEllipsisVertical className="h-5 w-5 text-gray-700 dark:text-gray-200" />
                        </MenuButton>
                        <MenuItems
                          anchor="bottom end"
                          className="z-50 mt-1 w-52 rounded-xl border border-gray-200 bg-white p-1 shadow-xl focus:outline-none dark:border-gray-700 dark:bg-gray-800"
                        >
                          <MenuItem>
                            <button
                              className={menuItemClass}
                              onClick={() => {
                                setVideoInfo({
                                  title: title,
                                  prompt: prompt,
                                  gpt_answer: gpt_answer,
                                  music: music,
                                  output: output,
                                });
                                setShowVideoModal(true);
                              }}
                            >
                              <FaRegEye className="h-4 w-4 text-blue-500" />
                              Video details
                            </button>
                          </MenuItem>

                          <MenuItem disabled={!isEditable}>
                            <button
                              disabled={!isEditable}
                              className={menuItemClass}
                              title={
                                isEditable
                                  ? "Open the scenes of this video"
                                  : `Cannot edit while ${status}`
                              }
                              onClick={() => navigate("/videos/" + id + "/")}
                            >
                              <FaPencilAlt className="h-4 w-4 text-orange-500" />
                              Edit scenes
                            </button>
                          </MenuItem>

                          <MenuItem disabled={!isRenderable}>
                            <button
                              disabled={!isRenderable}
                              className={menuItemClass}
                              title={
                                isRenderable
                                  ? "Render this video"
                                  : `Cannot render while ${status}`
                              }
                              onClick={() => {
                                setId(id);
                                setShowRenderModal(true);
                              }}
                            >
                              <GiProcessor className="h-4 w-4 text-purple-500" />
                              Render
                            </button>
                          </MenuItem>

                          {isResumable ? (
                            <MenuItem>
                              <button
                                className={menuItemClass}
                                title="Carry on generating this video"
                                onClick={() => {
                                  setId(id);
                                  setShowResumeModal(true);
                                }}
                              >
                                <FaRedo className="h-4 w-4 text-green-500" />
                                Carry on generating
                              </button>
                            </MenuItem>
                          ) : null}

                          <div className="my-1 border-t border-gray-200 dark:border-gray-700" />

                          <MenuItem disabled={!isDeletable}>
                            <button
                              disabled={!isDeletable}
                              className={`${menuItemClass} text-red-600 dark:text-red-400`}
                              title={
                                isDeletable
                                  ? "Delete this video"
                                  : `Cannot delete while ${status}`
                              }
                              onClick={() => {
                                setId(id);
                                setShowDeleteModal(true);
                              }}
                            >
                              <RiDeleteBin6Fill className="h-4 w-4" />
                              Delete
                            </button>
                          </MenuItem>
                        </MenuItems>
                      </Menu>
            </div>
          </li>;
        })}
      </ul>
    </>
  );
}
