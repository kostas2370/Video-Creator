import React, { useState } from "react";
import { createScene } from "../api/apiService";
import { toast } from "react-toastify";
import ReactLoading from "react-loading";
import { CloseModalButton } from "./ui/CloseModalButton";

export const TwitchSceneCreationModal = ({
  id,
  showModal,
  setShowModal,
  setItems,
}) => {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = (event) => {
    event.preventDefault();
    const formData = new FormData();
    formData.append("url", url);
    setLoading(true);

    createScene(id, formData).then((response) => {
      setLoading(false);
      if (response) {
        toast.success("Clip got added successfully !");
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
            className=" overflow-y-auto overflow-x-hidden fixed h-screen  flex items-center z-50 justify-center w-full inset-0 backdrop-filter backdrop-blur-md  max-h-full"
          >
            <div className="relative p-4 w-full max-w-md max-h-full">
              <div className="relative bg-white rounded-lg shadow dark:bg-gray-700">
                <div className="flex items-center justify-between p-4 md:p-5 border-b rounded-t dark:border-gray-600">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white text-center w-full">
                    Add Twitch Scene :
                  </h3>
                  <CloseModalButton setShowModal={setShowModal}/>
                </div>
                <form className="p-4 md:p-5" onSubmit={onSubmit}>
                  <div className="grid gap-4 mb-4 grid-cols-2">
                    <div className="col-span-2">
                      <label
                        htmlFor="name"
                        className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                      >
                        Twitch Clip Url :
                      </label>
                      <input
                        type="url"
                        name="url"
                        id="url"
                        className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500 dark:focus:border-primary-500"
                        placeholder="https://www.twitch.tv/streamer/clip/123"
                        required=""
                        onChange={(e) => setUrl(e.target.value)}
                      ></input>
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
                            fill-rule="evenodd"
                            d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z"
                            clip-rule="evenodd"
                          ></path>
                        </svg>
                        Add new Clip
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
      ) : (
        <></>
      )}
    </>
  );
};
