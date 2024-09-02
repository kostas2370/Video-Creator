import { Card, Typography } from "@material-tailwind/react";
import { useState } from "react";
import { FaRegEye, FaPencilAlt } from "react-icons/fa";
import { RiDeleteBin6Fill } from "react-icons/ri";
import { DeleteModal } from "./DeleteModal";
import { deleteVideo } from "../api/apiService";
import { VideoInfoModal } from "./VideoInfoModal";
import { GiProcessor } from "react-icons/gi";
import { RenderModal } from "./RenderModal";
import { useNavigate } from "react-router-dom";

const TABLE_HEAD = ["Video Title", "Status", "Video Type", "Actions"];

export function DefaultTable({ data, setVideos, loaded }) {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [showRenderModal, setShowRenderModal] = useState(false);
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

      <VideoInfoModal
        showModal={showVideoModal}
        setShowModal={setShowVideoModal}
        videoInfo={videoInfo}
      />

      <Card className="h-full w-full overflow-y-scroll">
        <table className="w-full h-full min-w-max table-fixed text-center">
          <thead>
            <tr>
              <th className="border-b border-blue-gray-100 bg-blue-gray-50 pt-4 pb-4 text-center w-1/2">
                <Typography
                  variant="small"
                  color="blue-gray"
                  className="font-normal leading-none opacity-70"
                >
                  Video Title
                </Typography>
              </th>
              <th className="border-b border-blue-gray-100 bg-blue-gray-50 pt-4 pb-4 text-center w-1/6">
                <Typography
                  variant="small"
                  color="blue-gray"
                  className="font-normal leading-none opacity-70"
                >
                  Status
                </Typography>
              </th>
              <th className="border-b border-blue-gray-100 bg-blue-gray-50 pt-4 pb-4 text-center w-1/6">
                <Typography
                  variant="small"
                  color="blue-gray"
                  className="font-normal leading-none opacity-70"
                >
                  Video Type
                </Typography>
              </th>
              <th className="border-b border-blue-gray-100 bg-blue-gray-50 pt-4 pb-4 text-center w-1/6">
                <Typography
                  variant="small"
                  color="blue-gray"
                  className="font-normal leading-none opacity-70"
                >
                  Actions
                </Typography>
              </th>
            </tr>
          </thead>
          <tbody>
            {data.map(
              (
                { title, status, video_type, output, id, prompt, music, gpt_answer },
                index
              ) => {
                const isLast = index === data.length - 1;
                const classes = isLast
                  ? "p-4"
                  : "p-4 border-b border-blue-gray-50";
                const isCompleted = status === "COMPLETED";
                const isRenderable = isCompleted || status === "READY";

                const renderIconColor = isRenderable
                  ? "text-purple-500 hover:text-red-300"
                  : "text-gray-400 ";

                const pencilIcon =
                  status === "READY" || isCompleted
                    ? "text-orange-500 hover:text-orange-300"
                    : "text-gray-400 disabled";

                const deleteIcon =
                  status !== "RENDERING"
                    ? "text-red-500 hover:text-red-300"
                    : "text-gray-400 disabled";

                return (
                  <tr key={title}>
                    <td className={`${classes} w-1/2`}>
                      <Typography
                        variant="small"
                        color="blue-gray"
                        className="text-center font-bold"
                      >
                        {title}
                      </Typography>
                    </td>
                    <td className={`${classes} w-1/6`}>
                      <Typography
                        variant="small"
                        color="blue-gray"
                        className="font-normal text-center"
                      >
                        {status}
                      </Typography>
                    </td>
                    <td className={`${classes} w-1/6`}>
                      <Typography
                        variant="small"
                        color="blue-gray"
                        className="font-normal text-center"
                      >
                        {video_type}
                      </Typography>
                    </td>
                    <td className={`${classes} w-1/6`}>
                      <Typography
                        variant="small"
                        color="blue-gray"
                        className="font-medium text-center"
                      >
                        <div className="grid grid-cols-4">
                          <FaRegEye
                            className="w-5 h-5 text-blue-500 hover:text-blue-300"
                            onClick={(e) => {
                              setVideoInfo({
                                title: title,
                                prompt: prompt,
                                gpt_answer: gpt_answer,
                                music: music,
                                output: output,
                              });
                              setShowVideoModal(true);
                            }}
                          />
                          <FaPencilAlt
                            className={`w-5 h-5 ${pencilIcon}`}
                            onClick={(event) => {
                              navigate("/videos/" + id + "/");
                            }}
                          />
                          <GiProcessor
                            onClick={(event) => {
                              if (status !== "RENDERING" && status !== "FAILED") {
                                setId(id);
                                setShowRenderModal(true);
                              }
                            }}
                            className={`w-5 h-5 ${renderIconColor}`}
                          />
                          <RiDeleteBin6Fill
                            className={`w-5 h-5 ${deleteIcon} text-center`}
                            onClick={(event) => {
                              if (status !== "RENDERING") {
                                setShowDeleteModal(true);
                                setId(id);
                              }
                            }}
                          />
                        </div>
                      </Typography>
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
