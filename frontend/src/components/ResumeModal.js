import React, { useEffect, useRef } from "react";
import { toast } from "react-toastify";
import { resumeVideo } from "../api/apiService";
import { pollVideo } from "../api/pollVideo";
import { FaRedo } from "react-icons/fa";
import { CloseModalButton } from "./ui/CloseModalButton";

export function ResumeModal({ showModal, setShowModal, id, setItems, name }) {
  const pollRef = useRef(null);

  useEffect(() => () => pollRef.current?.cancel(), []);

  const patchItem = (changes) => {
    if (!setItems) return;
    setItems((prevItems) =>
      prevItems.map((item) => (item.id === id ? { ...item, ...changes } : item))
    );
  };

  const ResumeClick = async () => {
    setShowModal(false);

    const response = await resumeVideo(id);

    if (!response.ok) {
      toast.error(response.message);
      return;
    }

    patchItem({ status: "GENERATION" });
    toast.info("Picking the generation up where it stopped...");

    pollRef.current = pollVideo(id, {
      onUpdate: (video) => patchItem({ status: video.status }),
    });

    const { outcome, video } = await pollRef.current.promise;

    if (outcome !== "SETTLED") {
      toast.error(
        "Lost track of the generation. Reload the page to see where it got to."
      );
      return;
    }

    patchItem({ status: video.status });

    if (video.status === "FAILED") {
      toast.error("It stopped again. The provider may still be unavailable.");
      return;
    }

    toast.success("The video is ready to render");
  };

  if (!showModal) {
    return null;
  }

  return (
    <div
      id="resumeModal"
      tabIndex="-1"
      className="overflow-y-auto overflow-x-hidden fixed h-screen my-auto flex items-center z-50 justify-center w-full inset-0 backdrop-filter backdrop-blur-md max-h-full"
    >
      <div className="relative p-4 w-full max-w-md h-full md:h-auto">
        <div className="relative p-4 text-center bg-white rounded-lg shadow dark:bg-gray-800 sm:p-5">
          <CloseModalButton setShowModal={setShowModal} />

          <FaRedo className="text-gray-400 dark:text-gray-500 w-11 h-11 mb-3.5 mx-auto" />
          <p className="mb-2 text-gray-500 dark:text-gray-300">
            Carry on generating {name}?
          </p>
          <p className="mb-4 text-xs text-gray-400 dark:text-gray-400">
            Only the lines with no narration and the shots with no image are made
            again, so nothing already generated is paid for twice.
          </p>
          <div className="flex justify-center items-center space-x-4">
            <button
              type="button"
              className="py-2 px-3 text-sm font-medium text-red-500 bg-white rounded-lg border border-gray-200 hover:bg-gray-100 focus:ring-4 focus:outline-none focus:ring-primary-300 hover:text-gray-900 focus:z-10 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-500 dark:hover:text-white dark:hover:bg-gray-600 dark:focus:ring-gray-600"
              onClick={() => setShowModal(false)}
            >
              No, cancel
            </button>
            <button
              type="submit"
              className="py-2 px-3 text-sm font-medium text-center text-white bg-green-600 rounded-lg hover:bg-green-700 focus:ring-4 focus:outline-none focus:ring-green-300 dark:bg-green-600 dark:hover:bg-green-700 dark:focus:ring-green-900"
              onClick={() => ResumeClick()}
            >
              Yes, carry on
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
