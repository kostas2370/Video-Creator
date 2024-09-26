import React, { useState } from "react";
import { createScene } from "../api/apiService";
import { toast } from "react-toastify";
import ReactLoading from "react-loading";
import { CloseModalButton } from "./ui/CloseModalButton";

export const SceneCreationModal = ({
  id,
  showModal,
  setShowModal,
  setItems,
}) => {
  const [text, setText] = useState("");
  const [imageDescription, setImageDescription] = useState("");
  const [image, setImage] = useState(null);
  const [isLast, setIsLast] = useState(false);
  const [withAudio, setWithAudio] = useState(false);
  const [loading, setLoading] = useState(false);

  const onSubmit = (event) => {
    event.preventDefault();
    const formData = new FormData();
    formData.append("text", text);
    formData.append("image_description", imageDescription);
    if (image){
        formData.append("image", image);
    }

    formData.append("is_last", isLast)
    formData.append("with_audio", withAudio)

    setLoading(true);

    createScene(id, formData).then((response) => {
      setLoading(false);
      if (response) {
        toast.success("Scene got added successfully !");
        setItems(true);
        setShowModal(false);
      }
    });
    
  };

  return (
    <>
      {showModal ? (
        <>
          <div
            id="crud-modal"
            tabIndex="-1"
            aria-hidden="false"
            className="overflow-y-auto overflow-x-hidden fixed h-screen  flex items-center z-50 justify-center w-full md:inset-0 backdrop-filter backdrop-blur-md  max-h-full"
          >
            <div className="relative p-4 w-full max-w-md max-h-full">
              <div className="relative bg-white rounded-lg shadow dark:bg-gray-700">
                <div className="flex items-center justify-between p-4 md:p-5 border-b rounded-t dark:border-gray-600">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white text-center w-full">
                    Add scene :
                  </h3>
                  <CloseModalButton setShowModal={setShowModal} />
                </div>
                <form className="p-4 md:p-5" onSubmit={onSubmit}>
                  <div className="grid gap-4 mb-4 grid-cols-2">
                    {/* Text input */}
                    <div className="col-span-2">
                      <label
                        htmlFor="text"
                        className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                      >
                        Text :
                      </label>
                      <input
                        type="text"
                        name="text"
                        id="text"
                        className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500 dark:focus:border-primary-500"
                        placeholder="Hello ! My name is viddie"
                        required=""
                        onChange={(e) => setText(e.target.value)}
                      ></input>
                    </div>

                    <div className="col-span-2">
                      <label
                        htmlFor="image_description"
                        className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                      >
                        Image Description :
                      </label>
                      <input
                        type="text"
                        name="image_description"
                        id="image_description"
                        className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500 dark:focus:border-primary-500"
                        placeholder="A robot saying hi!"
                        required=""
                        onChange={(e) => setImageDescription(e.target.value)}
                      ></input>
                    </div>

                    <div className="col-span-2">
                      <label
                        htmlFor="file_input"
                        className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                      >
                        Upload File:
                      </label>
                      <input
                        type="file"
                        name="file"
                        id="file_input"
                        className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg block w-full p-2 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white"
                        onChange={(e) => setImage(e.target.files[0])}
                      />
                    </div>

                    <div className="col-span-2 flex justify-center items-center space-x-6 py-2">
                      <div className="flex items-center">
                        <input
                          type="checkbox"
                          id="with_audio"
                          className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500"
                          checked={withAudio}
                          onChange={() => setWithAudio(!withAudio)}
                        />
                        <label
                          htmlFor="with_audio"
                          className="ml-2 text-sm font-medium text-gray-900 dark:text-white"
                        >
                          With Audio
                        </label>
                      </div>

                      <div className="flex items-center">
                        <input
                          type="checkbox"
                          id="is_last"
                          className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500"
                          checked={isLast}
                          onChange={() => setIsLast(!isLast)}
                        />
                        <label
                          htmlFor="is_last"
                          className="ml-2 text-sm font-medium text-gray-900 dark:text-white"
                        >
                          Is Last
                        </label>
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-center">
                    {!loading ? (
                      <button
                        type="submit"
                        className="text-white inline-flex items-center bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
                      >
                        <svg
                          className="me-1 -ms-1 w-5 h-5"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                          xmlns="http://www.w3.org/2000/svg"
                        >
                          <path
                            fillRule="evenodd"
                            d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z"
                            clipRule="evenodd"
                          ></path>
                        </svg>
                        Add new scene
                      </button>
                    ) : (
                      <ReactLoading
                        type="spokes"
                        color="#0000FF"
                        height={100}
                        width={50}
                      />
                    )}
                  </div>
                </form>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </>
  );
};
