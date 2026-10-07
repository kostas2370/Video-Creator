import React, { useEffect, useRef, useState } from "react";
import { toast } from "react-toastify";
import { getVideo, renderVideo } from "../api/apiService";
import { waitForVideo } from "../api/waitForVideo";
import { GiProcessor } from "react-icons/gi";
import { CloseModalButton } from "./ui/CloseModalButton";

export function RenderModal({
  showModal,
  setShowModal,
  id,
  setItems,
  name,
  onFinished,
  onUpdate,
  onPendingChange,
}) {
  const pollRef = useRef(null);
  const pendingRef = useRef(false);
  const [audioCheck, setAudioCheck] = useState({ loading: true, scenes: [], failed: false });
  useEffect(() => {
    if (!showModal) return;
    let cancelled = false;
    setAudioCheck({ loading: true, scenes: [], failed: false });
    getVideo(id).then(response => {
      if (cancelled) return;
      const scenes = response.data?.scenes || [];
      setAudioCheck({
        loading: false, failed: !response.ok,
        scenes: scenes.flatMap((scene, index) => scene.narration_status === "missing" ? [index + 1] : []),
      });
    });
    return () => { cancelled = true; };
  }, [showModal, id]);

  useEffect(() => () => pollRef.current?.cancel(), []);

  const patchItem = (changes) => {
    onUpdate?.(changes);
    if (!setItems) return;
    setItems((prevItems) =>
      prevItems.map((item) => (item.id === id ? { ...item, ...changes } : item))
    );
  };

  const RenderClick = async (event) => {
    if (pendingRef.current || audioCheck.loading) return;
    pendingRef.current = true;
    onPendingChange?.(true);
    setShowModal(false);

    const response = await renderVideo(id);

    if (!response.ok) {
      pendingRef.current = false;
      onPendingChange?.(false);
      toast.error(response.message);
      return;
    }

    patchItem({ status: "RENDERING" });
    onPendingChange?.(false);
    toast.info("Video now is on rendering status");

    pollRef.current = waitForVideo(id, {
      onUpdate: (video) => patchItem({ status: video.status }),
    });

    const { outcome, video } = await pollRef.current.promise;
    if (outcome === "CANCELLED") return;

    pendingRef.current = false;

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

    if (onFinished) onFinished(video);
  };

  return (
    <>
      {showModal ? (
        <>
          <div
            id="renderModal"
            tabIndex="-1"
            role="dialog"
            aria-modal="true"
            aria-label="Render video confirmation"
            className=" overflow-y-auto overflow-x-hidden fixed h-screen my-auto  flex items-center z-50 justify-center w-full inset-0 backdrop-filter backdrop-blur-md  max-h-full"
          >
            <div className="relative p-4 w-full max-w-md h-full md:h-auto">
              <div className="relative p-4 text-center bg-white rounded-lg shadow dark:bg-gray-800 sm:p-5">
                <CloseModalButton setShowModal={setShowModal} />

                <GiProcessor className="text-gray-400 dark:text-gray-500 w-11 h-11 mb-3.5 mx-auto" />
                <p className="mb-4 text-gray-500 dark:text-gray-300">
                  Are you sure you want to render this video : {name}?
                </p>
                {audioCheck.loading && <p role="status" className="mb-4 text-sm text-gray-500">Checking narration…</p>}
                {audioCheck.scenes.length > 0 && <div role="status" className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-left text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
                  <p className="font-semibold">Missing narration in {audioCheck.scenes.length === 1 ? "scene" : "scenes"} {audioCheck.scenes.join(", ")}</p>
                  <p className="mt-1">These scenes will render without narration. Cancel to retry audio in the editor, or continue with the available audio.</p>
                </div>}
                {audioCheck.failed && <p role="status" className="mb-4 text-sm text-amber-700 dark:text-amber-300">Narration could not be checked. You can still render, or cancel and review the scenes.</p>}
                <div className="flex justify-center items-center space-x-4">
                  <button
                    type="button"
                    className="py-2 px-3 text-sm font-medium text-red-500 bg-white rounded-lg border border-gray-200 hover:bg-gray-100 focus:ring-4 focus:outline-none focus:ring-primary-300 hover:text-gray-900 focus:z-10 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-500 dark:hover:text-white dark:hover:bg-gray-600 dark:focus:ring-gray-600"
                    onClick={(e) => setShowModal(false)}
                  >
                    No, cancel
                  </button>
                  <button
                    type="button"
                    disabled={audioCheck.loading}
                    className="py-2 px-3 text-sm font-medium text-center text-white bg-green-600 rounded-lg hover:bg-red-700 focus:ring-4 focus:outline-none focus:ring-red-300 dark:bg-red-500 dark:hover:bg-red-600 dark:focus:ring-red-900"
                    onClick={(e) => RenderClick()}
                  >
                    {audioCheck.scenes.length ? "Render anyway" : "Yes, I'm sure"}
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
