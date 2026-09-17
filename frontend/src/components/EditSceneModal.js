import React, { useState, useEffect } from "react";
import {  updateScene, generateScene } from "../api/apiService";
import { toast } from "react-toastify";
import ReactLoading from "react-loading";
export const EditSceneModal = ({
  showModal,
  setShowModal,
  scene_info,
  setUpdate,
}) => {
  const [sceneText, setSceneText] = useState(scene_info.dialogue);
  const [promptText, setPromptText] = useState("");

  const [loading, setLoading] = useState(false);

  const updateText = async () => {
    setLoading(true);

    let data = { text: sceneText };
    updateScene(scene_info.id, data).then((response) => {
      setLoading(false);
      if (response) {
        toast.success("Scene Updated sucessfully");
        setUpdate(true);
        setPromptText("")
        setShowModal(false);
      }
    });
  };


  const generateText = async () => {
    setLoading(true);

    let data = { text: promptText };
    generateScene(scene_info.id, data).then((response) => {
      setLoading(false);
      if (response) {
        setSceneText(response.text)
        
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
          <div className="relative p-6 w-full max-w-3xl max-h-full bg-blue-gray-200">
            <div className="relative bg-white rounded-lg shadow dark:bg-gray-700">
              <div className="flex items-center justify-between p-4 md:p-5 border-b rounded-t dark:border-gray-600">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white text-center w-full">
                  Edit scene :
                </h3>
                <button
                  type="button"
                  className="text-gray-400 bg-transparent hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm w-8 h-8 ms-auto inline-flex justify-center items-center dark:hover:bg-gray-600 dark:hover:text-white"
                  onClick={() => {setShowModal(false); setSceneText(scene_info.dialogue); setPromptText("")}}
                >
                  <svg
                    className="w-3 h-3"
                    aria-hidden="true"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 14 14"
                  >
                    <path
                      stroke="currentColor"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M1 1l6 6m0 0l6 6M7 7l6-6M7 7l-6 6"
                    />
                  </svg>
                  <span className="sr-only">Close modal</span>
                </button>
              </div>
              <div className="p-4 md:p-5">
                <div className="grid gap-4 mb-4 grid-cols-2">
                  <div className="col-span-2 sm:col-span-1">
                    <label
                      htmlFor="dialogue"
                      className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                    >
                      Dialogue:
                    </label>
                    <textarea
                      className="text-sm rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-4 h-40 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500 dark:focus:border-primary-500"
                      id="dialogue"
                      onChange={(e) => {
                        setSceneText(e.target.value);
                      }}
                      value={sceneText}
                    ></textarea>
                    <div className="flex justify-center pt-4">
                      {!loading ? (
                        <button
                          type="submit"
                          className="text-white inline-flex items-center bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
                          onClick={(e) => {
                            updateText();
                          }}
                        >
                          Update
                        </button>
                      ) : (
                        <div className="flex justify-center  ">
                          <ReactLoading
                            type="spokes"
                            color="#0000FF"
                            height={100}
                            width={50}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="col-span-2 sm:col-span-1">
                    <label
                      htmlFor="dialogue"
                      className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                    >
                      Prompt:
                    </label>
                    <textarea
                      className="text-sm rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-4 h-40 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500 dark:focus:border-primary-500"
                      id="prompt"
                      value={promptText}
                      onChange={(e) => {
                        setPromptText(e.target.value);
                      }}
                    ></textarea>
                    <div className="flex justify-center pt-4">
                    {!loading ? (
                        <button
                          type="submit"
                          className="text-white inline-flex items-center bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
                          onClick={(e) => {
                            generateText();
                          }}
                        >
                          Generate
                        </button>
                      ) : (
                        <div className="flex justify-center  ">
                          <ReactLoading
                            type="spokes"
                            color="#0000FF"
                            height={100}
                            width={50}
                          />
                        </div>
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
