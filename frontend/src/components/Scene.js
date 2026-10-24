import { DeferredDialog } from "./ui/DeferredDialog";
import { RememberedDetails } from "./ui/RememberedDetails";
import { formatDuration } from "../utils/timing";
import { isVideo } from "../utils/media";
import React, { lazy, useState } from "react";
import { Menu, MenuButton, MenuItems, MenuItem } from "@headlessui/react";
import { FaPencilAlt } from "react-icons/fa";
import { IoTrashBinSharp } from "react-icons/io5";
import { DeleteModal } from "./DeleteModal";
import { HiOutlinePencilSquare, HiOutlineEllipsisVertical } from "react-icons/hi2";
import { deleteImageScene, deleteScene, updateScene } from "../api/apiService";
import { API_HOST } from "../endpoints";
import { SceneOverlays } from "./SceneOverlays";
import { SceneCaptions } from "./SceneCaptions";
import { SceneAudio } from "./SceneAudio";
import { SceneMotion } from "./SceneMotion";
import { SceneTiming } from "./SceneTiming";
import { toast } from "react-toastify";

const EditSceneModal = lazy(() => import("./EditSceneModal").then(module => ({ default: module.EditSceneModal })));
const EditSceneImageModal = lazy(() => import("./EditSceneImageModal").then(module => ({ default: module.EditSceneImageModal })));

const formatFrameClasses = {
  LANDSCAPE: "aspect-video w-full",
  PORTRAIT: "mx-auto h-[min(65vh,420px)] max-w-full aspect-[9/16]",
  SQUARE: "mx-auto aspect-square w-full max-w-[420px]",
};

export const Scene = ({ manual, scene, setUpdated, onRemoveScene, video_format = "LANDSCAPE", index = 0, reorderHandle, onTiming, timingDisabled, timingSaving, onMotion, motionDisabled, motionSaving, nextScene, transitionControl }) => {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showDeleteSceneModal, setShowDeleteSceneModal] = useState(false);

  const [showEditModal, setShowEditModal] = useState(false);
  const [showEditImageModal, setShowEditImageModal] = useState(false);

  const MEDIA_URL = API_HOST;
  const [retryingNarration, setRetryingNarration] = useState(false);
  const retryNarration = async () => {
    if (retryingNarration) return;
    setRetryingNarration(true);
    try {
      const response = await updateScene(scene.id, { text: scene.text });
      if (response.ok) {
        if (response.data?.narration_status === "available") toast.success("Narration is ready");
        else toast.warning("Narration is still unavailable. You can retry later or render with the available audio.");
        setUpdated(true);
      }
    } finally { setRetryingNarration(false); }
  };

  return (
    <>
      <DeleteModal
        showModal={showDeleteModal}
        setShowModal={setShowDeleteModal}
        id={scene?.scene_image?.id}
        setItems={setUpdated}
        deleteFunction={deleteImageScene}
        name="image"
        mode="image"
      />

    <DeleteModal
        showModal={showDeleteSceneModal}
        setShowModal={setShowDeleteSceneModal}
        id={scene?.id}
        setItems={setUpdated}
        deleteFunction={onRemoveScene ? () => onRemoveScene(scene) : deleteScene}
        recoveryHint={onRemoveScene ? "You can undo this or restore the scene from Project extras → Recently deleted for 7 days." : undefined}
        name="Scene"
        mode="image"
      />

      <DeferredDialog open={showEditModal} onClose={() => setShowEditModal(false)}><EditSceneModal
        showModal={showEditModal}
        setShowModal={setShowEditModal}
        scene_info={{ dialogue: scene.text, id: scene.id, manual }}
        setUpdate={setUpdated}
      /></DeferredDialog>
      <DeferredDialog open={showEditImageModal} onClose={() => setShowEditImageModal(false)}><EditSceneImageModal
        showModal={showEditImageModal}
        setShowModal={setShowEditImageModal}
        scene_info={{
          image: MEDIA_URL + scene?.scene_image?.file,
          scene_id: scene.id,
          video_id: scene.video,
          scene_image_id: scene?.scene_image?.id,
          prompt: scene.scene_image?.prompt,
          with_audio: scene.scene_image?.with_audio,
          video_format,
        }}
        setUpdate={setUpdated}
      /></DeferredDialog>
      <article id={`scene-${scene.id}`} className="editor-panel scroll-mt-44 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-5 py-4 dark:border-gray-700">
          <div className="flex items-center gap-2">{reorderHandle}<h2 className="flex items-center gap-3 font-semibold text-gray-900 dark:text-white"><span className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-sm text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">{index + 1}</span>Scene {index + 1}</h2></div>
          <div className="flex items-center gap-3"><span className="rounded-lg bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500 dark:bg-gray-700 dark:text-gray-300">{formatDuration(scene.timing?.duration)}</span><Menu as="div" className="relative"><MenuButton aria-label={`Scene ${index + 1} actions`} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-gray-400 dark:hover:bg-gray-700"><HiOutlineEllipsisVertical className="h-5 w-5" /></MenuButton><MenuItems anchor="bottom end" className="z-50 mt-1 rounded-xl border border-gray-200 bg-white p-1 shadow-lg dark:border-gray-700 dark:bg-gray-800">{scene.scene_image?.file && <MenuItem><button type="button" disabled={timingDisabled} onClick={() => setShowDeleteModal(true)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-600 data-[focus]:bg-gray-50 disabled:opacity-40 dark:text-gray-300 dark:data-[focus]:bg-gray-700"><IoTrashBinSharp aria-hidden="true" className="h-4 w-4" />Remove visual</button></MenuItem>}<MenuItem><button type="button" disabled={timingDisabled} onClick={() => setShowDeleteSceneModal(true)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 data-[focus]:bg-red-50 disabled:opacity-40 dark:text-red-400 dark:data-[focus]:bg-red-900/20"><IoTrashBinSharp aria-hidden="true" className="h-4 w-4" />Delete scene</button></MenuItem></MenuItems></Menu></div>
        </header>
        <div className="grid items-start gap-5 p-4 sm:p-5 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <div className="min-w-0">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Source visual</h3><div className="flex flex-wrap items-center gap-1"><button type="button" disabled={timingDisabled} onClick={() => setShowEditImageModal(true)} className="flex items-center gap-2 rounded-lg px-2 py-1 text-sm font-medium text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-gray-700"><HiOutlinePencilSquare className="h-4 w-4" />{scene.scene_image?.file ? "Edit visual" : "Add visual"}</button></div></div>
            <div className={`relative overflow-hidden rounded-xl bg-gray-100 dark:bg-gray-900 ${formatFrameClasses[video_format] || formatFrameClasses.LANDSCAPE}`}>
              {scene.scene_image?.file ? (isVideo(scene.scene_image.file) ? <video controls playsInline preload="metadata" src={MEDIA_URL + scene.scene_image.file} className="h-full w-full bg-black object-cover" /> : <img src={MEDIA_URL + scene.scene_image.file} alt={scene.scene_image.prompt || `Scene ${index + 1} visual`} className="h-full w-full object-cover" />) : <div className="flex h-full w-full items-center justify-center text-sm text-gray-400">No visual yet</div>}

            </div>

            {scene.scene_image?.prompt && <details className="mt-4"><summary className="cursor-pointer text-xs font-medium text-gray-500 dark:text-gray-400">Visual prompt</summary><p className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap break-words text-xs leading-relaxed text-gray-500 dark:text-gray-400">{scene.scene_image.prompt}</p></details>}
          </div>
          <div className="min-w-0">
            <div className="mb-3 flex items-center justify-between"><h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">{manual ? "Scene text" : "Script & narration"}</h3><button type="button" disabled={timingDisabled} aria-label={manual ? "Edit scene text" : "Edit script"} onClick={() => setShowEditModal(true)} className="flex items-center gap-2 rounded-lg px-2 py-1 text-sm font-medium text-blue-600 hover:bg-blue-50 disabled:opacity-40 dark:text-blue-400 dark:hover:bg-gray-700"><FaPencilAlt className="h-3 w-3" />{manual ? "Edit text" : "Edit script"}</button></div>
            <p className="editor-inset max-h-64 overflow-y-auto whitespace-pre-wrap break-words rounded-xl bg-gray-50 p-4 text-sm leading-7 dark:bg-gray-900/40 text-gray-700 dark:text-gray-200">{scene.text || (manual ? "No caption text yet." : "No dialogue yet.")}</p>
            {scene.narration_status === "missing" ? <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-900/20">
              <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">Narration unavailable</p>
              <p className="mt-1 text-xs leading-relaxed text-amber-800 dark:text-amber-300">This scene has no narration audio. Your dialogue and visual are saved.</p>
              <button type="button" disabled={retryingNarration} onClick={retryNarration} className="mt-3 rounded-lg bg-amber-100 px-3 py-2 text-xs font-semibold text-amber-900 hover:bg-amber-200 disabled:opacity-50 dark:bg-amber-900/50 dark:text-amber-200">{retryingNarration ? "Retrying…" : "Retry narration"}</button>
            </div> : scene.narration_status === "disabled" ? <p className="mt-4 text-xs text-gray-400">{manual ? "Use Audio to record or upload a voiceover." : "Narration is off for this video"}</p> : ((scene.voiceover || scene.file) ? <details className="mt-4"><summary className="mb-3 cursor-pointer text-xs font-medium text-gray-500 dark:text-gray-400">Listen to original narration</summary><p className="mb-2 text-xs text-gray-500 dark:text-gray-400">Before audio edits. Use Preview edit to hear the current mix.</p><audio aria-label={`Scene ${index + 1} narration`} controls preload="none" key={scene.voiceover || scene.file} className="h-10 w-full"><source src={MEDIA_URL + (scene.voiceover || scene.file)} /></audio></details> : <p className="mt-4 text-xs text-gray-400">No narration yet</p>)}
            <div className="mt-4"><SceneAudio scene={scene} index={index} nextScene={nextScene} disabled={timingDisabled} onSaved={setUpdated} /></div>

          </div>

        </div>
        <RememberedDetails videoId={scene.video} panel="adjustScene" className="border-t border-gray-100 px-4 py-4 sm:px-5 dark:border-gray-700">
          <summary className="cursor-pointer text-sm font-semibold">Adjust scene <span className="ml-2 text-xs font-normal text-gray-500 dark:text-gray-400">Overlays, captions, timing &amp; motion</span></summary>
          <div className="mt-4 space-y-5">
            <div aria-label="Scene editing tools" className="flex flex-wrap items-center gap-2"><SceneOverlays scene={scene} index={index} disabled={timingDisabled} onSaved={setUpdated} videoFormat={video_format} /><SceneCaptions scene={scene} index={index} disabled={timingDisabled} onSaved={setUpdated} videoFormat={video_format} />{onMotion && <SceneMotion scene={scene} index={index} disabled={motionDisabled} saving={motionSaving} onChange={onMotion} videoFormat={video_format} />}</div>
            {(onTiming || transitionControl) && <div className="grid items-start gap-5 md:grid-cols-2">
              {onTiming && <div><h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400">Scene timing</h3><SceneTiming manual={manual} scene={scene} index={index} disabled={timingDisabled} saving={timingSaving} onChange={onTiming} /></div>}
              {transitionControl && <div><h3 className="mb-3 text-xs font-semibold text-gray-500 dark:text-gray-400">Transition to next scene</h3>{transitionControl}</div>}
            </div>}
          </div>
        </RememberedDetails>
      </article>
    </>
  );
};
