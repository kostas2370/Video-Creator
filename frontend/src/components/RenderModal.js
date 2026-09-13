import React, { useEffect, useRef } from "react";
import { toast } from "react-toastify";
import { renderVideo } from "../api/apiService";
import { pollVideo } from "../api/pollVideo";
import { GiProcessor } from "react-icons/gi";
import { CloseModalButton } from "./ui/CloseModalButton";

export function RenderModal({
  showModal,
  setShowModal,
  id,
  setItems,
  name,
  onFinished,
}) {
  // VideoPage mounts this modal without setItems, so every write has to be guarded.
  const pollRef = useRef(null);

  useEffect(() => () => pollRef.current?.cancel(), []);

  const patchItem = (changes) => {
    if (!setItems) return;
    setItems((prevItems) =>
      prevItems.map((item) => (item.id === id ? { ...item, ...changes } : item))
    );
  };

  const RenderClick = async (event) => {
    setShowModal(false);

    const response = await renderVideo(id);

    if (!response.ok) {
      // 409 means the video is not READY/COMPLETED — a real answer, not a failure to
      // render, so the row keeps whatever status it already had.
      toast.error(response.message);
      return;
    }

    patchItem({ status: "RENDERING" });
    toast.info("Video now is on rendering status");

    pollRef.current = pollVideo(id, {
      onUpdate: (video) => patchItem({ status: video.status }),
    });

    const { outcome, video } = await pollRef.current.promise;

    if (outcome !== "SETTLED") {
      toast.error(
        "Lost track of the render. Reload the page to see where it got to."
      );
      return;
    }

    patchItem({ status: video.status, output: video.output });

    if (video.status === "COMPLETED") {
      toast.success("Video now is completed");
    } else {
      toast.error("The render failed, probably you have to generate a new one");
    }

    // VideoPage has no item list to patch and refetches the whole video instead.
    if (onFinished) onFinished(video);
  };

  return (
    <>
      {showModal ? (
        <>
          <div
            id="renderModal"
            tabindex="-1"
            aria-hidden="true"
            class=" overflow-y-auto overflow-x-hidden fixed h-screen my-auto  flex items-center z-50 justify-center w-full md:inset-0 ackdrop-filter backdrop-blur-md  max-h-full"
          >
            <div class="relative p-4 w-full max-w-md h-full md:h-auto">
              <div class="relative p-4 text-center bg-white rounded-lg shadow dark:bg-gray-800 sm:p-5">
                <CloseModalButton setShowModal={setShowModal} />

                <GiProcessor className="text-gray-400 dark:text-gray-500 w-11 h-11 mb-3.5 mx-auto" />
                <p class="mb-4 text-gray-500 dark:text-gray-300">
                  Are you sure you want to render this video : {name}?
                </p>
                <div class="flex justify-center items-center space-x-4">
                  <button
                    type="button"
                    class="py-2 px-3 text-sm font-medium text-red-500 bg-white rounded-lg border border-gray-200 hover:bg-gray-100 focus:ring-4 focus:outline-none focus:ring-primary-300 hover:text-gray-900 focus:z-10 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-500 dark:hover:text-white dark:hover:bg-gray-600 dark:focus:ring-gray-600"
                    onClick={(e) => setShowModal(false)}
                  >
                    No, cancel
                  </button>
                  <button
                    type="submit"
                    class="py-2 px-3 text-sm font-medium text-center text-white bg-green-600 rounded-lg hover:bg-red-700 focus:ring-4 focus:outline-none focus:ring-red-300 dark:bg-red-500 dark:hover:bg-red-600 dark:focus:ring-red-900"
                    onClick={(e) => RenderClick()}
                  >
                    Yes, I'm sure
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      ) : (
        <></>
      )}
    </>
  );
}
