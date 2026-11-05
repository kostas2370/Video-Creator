import React, { useEffect, useRef } from "react";
import { toast } from "react-toastify";
import { resumeVideo } from "../api/apiService";
import { waitForVideo } from "../api/waitForVideo";
import { FaRedo } from "react-icons/fa";
import { EditorDialog, editorButton, editorSecondaryButton } from "./ui/EditorDialog";

export function ResumeModal({
  showModal,
  setShowModal,
  id,
  setItems,
  name,
  onFinished,
}) {
  const watcherRef = useRef(null);

  useEffect(() => () => watcherRef.current?.cancel(), []);

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

    watcherRef.current = waitForVideo(id, {
      onUpdate: (video) => patchItem({ status: video.status }),
    });

    const { outcome, video } = await watcherRef.current.promise;
    if (outcome === "CANCELLED") return;

    if (outcome !== "SETTLED") {
      toast.error(
        "Lost track of the generation. Reload the page to see where it got to."
      );
      return;
    }

    patchItem({ status: video.status });

    if (video.status === "FAILED") {
      toast.error("It stopped again. The provider may still be unavailable.");
    } else {
      toast.success("The video is ready to render");
    }

    if (onFinished) onFinished(video);
  };

  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title="Resume generation" description="Pick up where your video stopped." icon={FaRedo} maxWidth="max-w-lg" footer={<div className="flex justify-end gap-2">
    <button type="button" onClick={() => setShowModal(false)} className={editorSecondaryButton}>Cancel</button>
    <button type="button" onClick={ResumeClick} className={editorButton}>Resume generation</button>
  </div>}>
    <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900"><p className="break-words text-sm font-semibold">{name}</p><p className="mt-3 text-sm leading-relaxed text-gray-500 dark:text-gray-400">Only missing narration and visuals are requested again. Media already generated stays in your project.</p></div>
  </EditorDialog>;
}
