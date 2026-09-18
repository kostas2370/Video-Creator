import React, { useState } from "react";
import { updateSceneImage, generateSceneImage } from "../api/apiService";
import ReactLoading from "react-loading";
import { CloseModalButton } from "./ui/CloseModalButton";

import { toast } from "react-toastify";
export const EditSceneImageModal = ({
  showModal,
  setShowModal,
  scene_info,
  setUpdate,
}) => {

  const [file, setFile] = useState("");
  const [withAudio, setWithAudio] = useState(scene_info.with_audio ?? 0);
  const [loading, setLoading] = useState(false);
  const [description, setDescription] = useState(scene_info.prompt ?? "");

  const updateImage = async () => {
    setLoading(true);
    let with_audio = withAudio ? 1 : 0;

    const formData = new FormData();
    formData.append("image", file);
    formData.append("with_audio", with_audio);

    updateSceneImage(
      scene_info.scene_id,
      scene_info.scene_image_id,
      formData
    ).then((response) => {
      setLoading(false);
      if (response) {
        toast.success("Scene Image Updated sucessfully");
        setUpdate(true);
        setShowModal(false);
      }
    });
  };
 // eslint-disable-next-line
  const generateImage = async () => {
    setLoading(true);

    const formData = new FormData();
    formData.append("image_description", description);

    generateSceneImage(scene_info.scene_id, formData).then((response) => {
      setLoading(false);
      if (response) {
        toast.success("Scene Image Updated sucessfully");
        setUpdate(true);
        setShowModal(false);
      }
    });
  };

  return (
    <>
      {showModal && (
        <div
          id="crud-modal"
          tabIndex="-1"
          aria-hidden="false"
          className="overflow-y-auto overflow-x-hidden fixed h-screen flex items-center z-50 justify-center w-full inset-0 backdrop-blur-md max-h-full"
        >
          <div className="relative p-6 w-full max-w-3xl max-h-full">
            <div className="relative bg-white rounded-lg shadow dark:bg-gray-700">
              <div className="flex items-center justify-between p-4 md:p-5 border-b rounded-t dark:border-gray-600">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white text-center w-full">
                  Edit Scene Image:
                </h3>
                <CloseModalButton setShowModal={setShowModal} />
              </div>
              <div className="p-4 md:p-5">
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="col-span-2 sm:col-span-1">
                    <img
                      src={scene_info.image}
                      alt=""
                      className="object-cover h-48 w-full md:w-96"
                    />
                    <div className="flex items-center mb-4 pt-4">
                      <input
                        id="default-checkbox"
                        type="checkbox"
                        checked={withAudio}
                        className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                        onChange={(e) => setWithAudio(e.target.checked)}
                      />
                      <label
                        htmlFor="default-checkbox"
                        className="ms-2 text-sm font-medium text-gray-900 dark:text-gray-300"
                      >
                        With Audio
                      </label>
                    </div>
                  </div>

                  <div className="col-span-2 sm:col-span-1">
                    <div className="mb-4">
                      <label
                        htmlFor="image-upload"
                        className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                      >
                        Change Image
                      </label>
                      <input
                        id="image-upload"
                        type="file"
                        className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400"
                        onChange={(e) => setFile(e.target.files[0])}
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="description"
                        className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                      >
                        Image Description
                      </label>
                      <textarea
                        id="description"
                        rows="4"
                        className="block p-2.5 w-full text-sm text-gray-900 bg-gray-50 rounded-lg border border-gray-300 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                        placeholder="Write your description here..."
                        value={description}
                        onChange={(e) => {
                          setDescription(e.target.value);
                        }}
                      ></textarea>
                    </div>

                    <div className="flex justify-center space-x-4 mt-4">
                      {loading ? (
                        <ReactLoading
                          type="spokes"
                          color="#0000FF"
                          height={100}
                          width={50}
                        />
                      ) : (
                        <>
                          <button
                            onClick={(e) => {
                              updateImage();
                            }}
                            className="bg-blue-500 text-white font-bold py-2 px-4 rounded hover:bg-blue-700"
                          >
                            Update
                          </button>
                          <button
                            onClick={(e) => {
                              generateImage();
                            }}
                            className="bg-gray-500 text-white font-bold py-2 px-4 rounded hover:bg-gray-700"
                          >
                            Regenerate
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
