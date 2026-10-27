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
  const watcherRef = useRef(null);
  const pendingRef = useRef(false);
  const [exportPreset, setExportPreset] = useState("STANDARD");
  const [exportFps, setExportFps] = useState(24);
  const [audioCheck, setAudioCheck] = useState({ loading: true, scenes: [], failed: false });
  useEffect(() => {
    if (!showModal) return;
    let cancelled = false;
    setAudioCheck({ loading: true, scenes: [], failed: false });
    setExportPreset("STANDARD");
    setExportFps(24);
    getVideo(id).then(response => {
      if (cancelled) return;
      const scenes = response.data?.scenes || [];
      const settings = response.data?.settings || {};
      setExportPreset(["DRAFT", "STANDARD", "HIGH"].includes(settings.export_preset) ? settings.export_preset : "STANDARD");
      setExportFps([24, 30].includes(settings.export_fps) ? settings.export_fps : 24);
      setAudioCheck({
        loading: false, failed: !response.ok,
        scenes: scenes.flatMap((scene, index) => scene.narration_status === "missing" ? [index + 1] : []),
      });
    });
    return () => { cancelled = true; };
  }, [showModal, id]);

  useEffect(() => () => watcherRef.current?.cancel(), []);

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

    const response = await renderVideo(id, { export_preset: exportPreset, export_fps: exportFps });

    if (!response.ok) {
      pendingRef.current = false;
      onPendingChange?.(false);
      toast.error(response.message);
      return;
    }

    patchItem({ status: "RENDERING", settings: response.data?.video?.settings });
    onPendingChange?.(false);
    toast.info("Your video is queued for export.");

    watcherRef.current = waitForVideo(id, {
      onUpdate: (video) => patchItem({ status: video.status }),
    });

    const { outcome, video } = await watcherRef.current.promise;
    if (outcome === "CANCELLED") return;

    pendingRef.current = false;

    if (outcome !== "SETTLED") {
      toast.error(
        "Lost track of the render. Reload the page to see where it got to."
      );
      return;
    }

    patchItem({ status: video.status, output: video.output, render_error: video.render_error });

    if (video.status === "COMPLETED") {
      toast.success("Your video export is ready.");
    } else {
      toast.error(`${video.render_error?.message || "The export failed. Your project is saved. Retry the export from the editor."}${video.render_error?.reference ? ` Reference: ${video.render_error.reference}` : ""}`);
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
                <div className="mb-4 space-y-3 text-left text-sm text-gray-700 dark:text-gray-200">
                  <label className="block" htmlFor="export-quality">Export quality</label>
                  <select id="export-quality" value={exportPreset} disabled={audioCheck.loading} onChange={event => setExportPreset(event.target.value)} aria-describedby="export-quality-help" className="w-full rounded-lg border border-gray-300 bg-white p-2 dark:border-gray-600 dark:bg-gray-700">
                    <option value="DRAFT">Draft — quick review</option>
                    <option value="STANDARD">Standard — balanced</option>
                    <option value="HIGH">High — best detail</option>
                  </select>
                  <p id="export-quality-help" className="text-xs text-gray-500 dark:text-gray-400">
                    {exportPreset === "DRAFT" ? "Faster encoding with more compression. Useful for reviewing edits." : exportPreset === "HIGH" ? "Preserves more source detail. Encoding takes longer and files are usually larger." : "Balances detail, encoding time, and file size. Matches the previous export quality."}
                  </p>
                  <label className="block" htmlFor="export-fps">Frame rate</label>
                  <select id="export-fps" value={exportFps} disabled={audioCheck.loading} onChange={event => setExportFps(Number(event.target.value))} aria-describedby="export-fps-help" className="w-full rounded-lg border border-gray-300 bg-white p-2 dark:border-gray-600 dark:bg-gray-700">
                    <option value={24}>24 fps</option>
                    <option value={30}>30 fps</option>
                  </select>
                  <p id="export-fps-help" className="text-xs text-gray-500 dark:text-gray-400">30 fps gives image motion more frames and may take longer to render. It does not add detail to source clips. Your project dimensions stay the same.</p>
                </div>
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
