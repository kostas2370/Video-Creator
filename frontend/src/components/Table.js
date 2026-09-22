import { Card, Typography } from "@material-tailwind/react";
import { useState } from "react";
import { Menu, MenuButton, MenuItems, MenuItem } from "@headlessui/react";
import { HiOutlineEllipsisVertical } from "react-icons/hi2";
import { FaRegEye, FaPencilAlt, FaRedo } from "react-icons/fa";
import { RiDeleteBin6Fill } from "react-icons/ri";
import { DeleteModal } from "./DeleteModal";
import { deleteVideo } from "../api/apiService";
import { VideoInfoModal } from "./VideoInfoModal";
import { GiProcessor } from "react-icons/gi";
import { RenderModal } from "./RenderModal";
import { ResumeModal } from "./ResumeModal";
import { useNavigate } from "react-router-dom";

const TABLE_HEAD = ["Video Title", "Status", "Video Type", "Actions"];

const menuItemClass =
  "flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-gray-700 data-[focus]:bg-gray-100 data-[disabled]:cursor-not-allowed data-[disabled]:opacity-40 dark:text-gray-200 dark:data-[focus]:bg-gray-700";

export function DefaultTable({ data, setVideos, loaded }) {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [showRenderModal, setShowRenderModal] = useState(false);
  const [showResumeModal, setShowResumeModal] = useState(false);
  const navigate = useNavigate();

  const [id, setId] = useState("");
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

      <Card className="h-full w-full overflow-y-scroll dark:bg-gray-800">
        <table className="w-full h-full min-w-max table-fixed text-center">
          <thead>
            <tr>
              <th className="border-b border-blue-gray-100 bg-blue-gray-50 dark:bg-gray-700 dark:border-gray-600 pt-4 pb-4 text-center w-1/2">
                <Typography
                  variant="small"
                  color="blue-gray"
                  className="font-normal leading-none opacity-70 dark:text-white"
                >
                  Video Title
                </Typography>
              </th>
              <th className="border-b border-blue-gray-100 bg-blue-gray-50 dark:bg-gray-700 dark:border-gray-600 pt-4 pb-4 text-center w-1/6">
                <Typography
                  variant="small"
                  color="blue-gray"
                  className="font-normal leading-none opacity-70 dark:text-white"
                >
                  Status
                </Typography>
              </th>
              <th className="border-b border-blue-gray-100 bg-blue-gray-50 dark:bg-gray-700 dark:border-gray-600 pt-4 pb-4 text-center w-1/6">
                <Typography
                  variant="small"
                  color="blue-gray"
                  className="font-normal leading-none opacity-70 dark:text-white"
                >
                  Video Type
                </Typography>
              </th>
              <th className="border-b border-blue-gray-100 bg-blue-gray-50 dark:bg-gray-700 dark:border-gray-600 pt-4 pb-4 text-center w-1/6">
                <Typography
                  variant="small"
                  color="blue-gray"
                  className="font-normal leading-none opacity-70 dark:text-white"
                >
                  Actions
                </Typography>
              </th>
            </tr>
          </thead>
          <tbody>
            {data?.map(
              (
                { title, status, video_type, output, id, prompt, music, gpt_answer },
                index
              ) => {
                const isLast = index === data.length - 1;
                const classes = isLast
                  ? "p-4"
                  : "p-4 border-b border-blue-gray-50 dark:border-gray-700";
                const isCompleted = status === "COMPLETED";
                const isRenderable = isCompleted || status === "READY";
                const isEditable = isRenderable;
                const isDeletable = status !== "RENDERING";
                const isResumable = status === "FAILED";

                return (
                  <tr key={id}>
                    <td className={`${classes} w-1/2`}>
                      <Typography
                        variant="small"
                        color="blue-gray"
                        className="text-center font-bold dark:text-white"
                      >
                        {title}
                      </Typography>
                    </td>
                    <td className={`${classes} w-1/6`}>
                      <Typography
                        variant="small"
                        color="blue-gray"
                        className="font-normal text-center dark:text-white"
                      >
                        {status}
                      </Typography>
                    </td>
                    <td className={`${classes} w-1/6`}>
                      <Typography
                        variant="small"
                        color="blue-gray"
                        className="font-normal text-center dark:text-white"
                      >
                        {video_type}
                      </Typography>
                    </td>
                    <td className={`${classes} w-1/6`}>
                      <Menu as="div" className="relative inline-block text-left">
                        <MenuButton
                          aria-label={`Actions for ${title}`}
                          className="rounded-full p-2 transition hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-400 dark:hover:bg-gray-700"
                        >
                          <HiOutlineEllipsisVertical className="h-5 w-5 text-gray-700 dark:text-gray-200" />
                        </MenuButton>
                        <MenuItems
                          anchor="bottom end"
                          className="z-50 mt-1 w-52 rounded-lg border border-gray-200 bg-white py-1 shadow-lg focus:outline-none dark:border-gray-700 dark:bg-gray-800"
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
                    </td>
                  </tr>
                );
              }
            )}
          </tbody>
        </table>
      </Card>
    </>
  );
}
