import { hasFullSceneDiagram } from "../utils/diagrams";
import { SceneDiagramPreview } from "./SceneDiagramPreview";
import { GenerationCost } from "./GenerationCost";
import { DeferredDialog } from "./ui/DeferredDialog";
import { formatDuration } from "../utils/timing";
import { isVideo } from "../utils/media";
import React, { lazy, Suspense, useState } from "react";
import { Menu, MenuButton, MenuItems, MenuItem, TabGroup, TabList, Tab, TabPanels, TabPanel } from "@headlessui/react";
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
import { SceneStartingFrame } from "./SceneStartingFrame";
import { SceneTextEditor } from "./SceneTextEditor";

const EditSceneImageModal = lazy(() => import("./EditSceneImageModal").then(module => ({ default: module.EditSceneImageModal })));

const InlineVideoPreview = lazy(() => import("./VideoPreview").then(module => ({ default: module.VideoPreview })));

const formatFrameClasses = {
  LANDSCAPE: "mx-auto aspect-video w-full max-w-[calc(42vh*16/9)]",
  PORTRAIT: "mx-auto h-[min(42vh,420px)] max-w-full aspect-[9/16]",
  SQUARE: "mx-auto aspect-square w-full max-w-[min(42vh,420px)]",
};

export const Scene = ({ video, previewDisabled = false, generationMode = "STANDARD", textDraft, onTextDraftChange, onTextSave, onTextRewrite, manual, scene, setUpdated, onRemoveScene, video_format = "LANDSCAPE", exportFps = 24, index = 0, reorderHandle, onTiming, timingDisabled, timingSaving, onMotion, motionDisabled, motionSaving, nextScene, transitionControl }) => {
  const [inspectorTab, setInspectorTab] = useState(0);
  const [stageMode, setStageMode] = useState("scene");
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showDeleteSceneModal, setShowDeleteSceneModal] = useState(false);

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

  const diagram = hasFullSceneDiagram(scene);
  const diagramEditor = <SceneOverlays scene={scene} index={index} disabled={timingDisabled} onSaved={setUpdated} videoFormat={video_format} label="Edit text diagram" />;
  const visualPrompt = scene.scene_image?.prompt;
  const promptShownInStartingFrame = scene.starting_frame_required && visualPrompt?.trim() === scene.starting_frame_description?.trim();

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
          generation_mode: generationMode,
          starting_frame_required: scene.starting_frame_required,
        }}
        setUpdate={setUpdated}
      /></DeferredDialog>
      <article id={`scene-${scene.id}`} className="editor-panel scroll-mt-44 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-5 py-4 dark:border-gray-700">
          <div className="flex items-center gap-2">{reorderHandle}<h2 className="flex items-center gap-3 font-semibold text-gray-900 dark:text-white"><span className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-sm text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">{index + 1}</span>Scene {index + 1}</h2></div>
          <div className="flex items-center gap-3"><span className="rounded-lg bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500 dark:bg-gray-700 dark:text-gray-300">{formatDuration(scene.timing?.duration)}</span><Menu as="div" className="relative"><MenuButton aria-label={`Scene ${index + 1} actions`} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-gray-400 dark:hover:bg-gray-700"><HiOutlineEllipsisVertical className="h-5 w-5" /></MenuButton><MenuItems modal={false} anchor="bottom end" className="z-50 mt-1 rounded-xl border border-gray-200 bg-white p-1 shadow-lg dark:border-gray-700 dark:bg-gray-800">{!diagram && scene.scene_image?.file && <MenuItem><button type="button" disabled={timingDisabled} onClick={() => setShowDeleteModal(true)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-600 data-[focus]:bg-gray-50 disabled:opacity-40 dark:text-gray-300 dark:data-[focus]:bg-gray-700"><IoTrashBinSharp aria-hidden="true" className="h-4 w-4" />Remove visual</button></MenuItem>}<MenuItem><button type="button" disabled={timingDisabled} onClick={() => setShowDeleteSceneModal(true)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 data-[focus]:bg-red-50 disabled:opacity-40 dark:text-red-400 dark:data-[focus]:bg-red-900/20"><IoTrashBinSharp aria-hidden="true" className="h-4 w-4" />Delete scene</button></MenuItem></MenuItems></Menu></div>
        </header>
        <div className="studio-layout">
          <section aria-label="Scene canvas" className="studio-stage min-w-0">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-1 rounded-xl bg-gray-200/60 p-1 dark:bg-white/5" role="group" aria-label="Canvas view">
                <button type="button" aria-pressed={stageMode === "scene"} onClick={() => setStageMode("scene")} className={`studio-view-button ${stageMode === "scene" ? "studio-view-active" : ""}`}>Scene visual</button>
                {video && <button type="button" aria-pressed={stageMode === "edit"} onClick={() => setStageMode("edit")} className={`studio-view-button ${stageMode === "edit" ? "studio-view-active" : ""}`}>Preview scene</button>}
              </div>
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{{ LANDSCAPE: "16:9", PORTRAIT: "9:16", SQUARE: "1:1" }[video_format] || "16:9"}</span>
            </div>
            {stageMode === "edit" && video ? <Suspense fallback={<p role="status" className="py-20 text-center text-sm text-gray-500">Loading player…</p>}><InlineVideoPreview video={video} selectedSceneId={scene.id} disabled={previewDisabled} compact sceneOnly /></Suspense> : <>
              <div className="studio-canvas flex min-h-64 items-center justify-center rounded-xl bg-gray-950 p-3">
            {diagram ? <div className="w-full max-w-[calc(42vh*16/9)]"><SceneDiagramPreview key={scene.id} scene={scene} videoFormat={video_format} controls /></div> : <div className={`relative overflow-hidden rounded-xl bg-gray-100 dark:bg-gray-900 ${formatFrameClasses[video_format] || formatFrameClasses.LANDSCAPE}`}>
              {scene.scene_image?.file ? (isVideo(scene.scene_image.file) ? <video controls playsInline preload="metadata" src={MEDIA_URL + scene.scene_image.file} className="h-full w-full bg-black object-cover" /> : <img src={MEDIA_URL + scene.scene_image.file} alt={scene.scene_image.prompt || `Scene ${index + 1} visual`} className="h-full w-full object-cover" />) : <div className="flex h-full w-full items-center justify-center text-sm text-gray-400">No visual yet</div>}

            </div>}

              </div>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">{video ? "Source visual · Preview scene to review captions, motion & audio." : "Source visual"}</p>
                {diagram ? diagramEditor : <button type="button" disabled={timingDisabled} onClick={() => setShowEditImageModal(true)} className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 disabled:opacity-40 dark:text-blue-300 dark:hover:bg-white/5"><HiOutlinePencilSquare aria-hidden="true" className="h-4 w-4" />{scene.scene_image?.file ? "Edit visual" : "Add visual"}</button>}
              </div>
            </>}
            {!diagram && (scene.starting_frame_required || scene.starting_frame) && <SceneStartingFrame generationMode={generationMode} scene={scene} index={index} disabled={timingDisabled} onSaved={setUpdated} />}
          </section>
          <aside aria-label="Scene inspector" className="studio-inspector min-w-0">
            <TabGroup selectedIndex={inspectorTab} onChange={setInspectorTab}>
              {scene.narration_status === "missing" && <button type="button" onClick={() => setInspectorTab(2)} className="w-full bg-amber-50 px-4 py-3 text-left text-xs font-semibold text-amber-800 dark:bg-amber-950/40 dark:text-amber-200">Narration needs attention → Open audio</button>}
              <TabList className="studio-tabs flex gap-1 border-b border-gray-200 p-2 dark:border-gray-700">
                {["Script", "Visual", "Audio", "Style", ...((onTiming || transitionControl) ? ["Timing"] : [])].map(label => <Tab key={label} className="min-w-0 flex-1 rounded-lg px-2 py-2.5 text-xs font-semibold text-gray-500 outline-none transition hover:text-gray-900 data-selected:bg-blue-50 data-selected:text-blue-700 data-focus:ring-2 data-focus:ring-blue-500 dark:text-gray-400 dark:hover:text-white dark:data-selected:bg-blue-500/15 dark:data-selected:text-blue-300">{label}</Tab>)}
              </TabList>
              <TabPanels className="studio-tab-panels p-4 sm:p-5">
                <TabPanel unmount={false}>
            <SceneTextEditor scene={scene} index={index} manual={manual} draft={textDraft} onDraftChange={onTextDraftChange} onSave={onTextSave} onRewrite={onTextRewrite} disabled={timingDisabled} />
                </TabPanel>
                <TabPanel unmount={false}>
                  <h3 className="text-sm font-semibold">Visual settings</h3>
                  <p className="mb-4 mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Replace your media or refine the visual for this scene.</p>
                  {diagram ? diagramEditor : <button type="button" disabled={timingDisabled} onClick={() => setShowEditImageModal(true)} className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40">Replace or generate visual</button>}


            {!diagram && visualPrompt && !promptShownInStartingFrame && <details className="mt-4"><summary className="cursor-pointer text-xs font-medium text-gray-500 dark:text-gray-400">Visual description</summary><p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Directions for what the scene shows. Narration is edited separately under Script.</p><p className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap break-words text-xs leading-relaxed text-gray-500 dark:text-gray-400">{scene.scene_image.prompt}</p></details>}
                </TabPanel>
                <TabPanel unmount={false}>
                  <h3 className="text-sm font-semibold">Scene audio</h3>
                  <p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Manage narration and the sound of this scene.</p>
            {scene.narration_status === "missing" ? <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-900/20">
              <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">Narration unavailable</p>
              <p className="mt-1 text-xs leading-relaxed text-amber-800 dark:text-amber-300">This scene has no narration audio. Your dialogue and visual are saved.</p>
              <GenerationCost refresh={scene} videoId={scene.video} sceneId={scene.id} operation="narration" />
              <button type="button" disabled={retryingNarration} onClick={retryNarration} className="mt-3 rounded-lg bg-amber-100 px-3 py-2 text-xs font-semibold text-amber-900 hover:bg-amber-200 disabled:opacity-50 dark:bg-amber-900/50 dark:text-amber-200">{retryingNarration ? "Retrying…" : "Retry narration"}</button>
            </div> : scene.narration_status === "disabled" ? <p className="mt-4 text-xs text-gray-400">{manual ? "Use Audio to record or upload a voiceover." : "Narration is off for this video"}</p> : ((scene.voiceover || scene.file) ? <details className="mt-4"><summary className="mb-3 cursor-pointer text-xs font-medium text-gray-500 dark:text-gray-400">Listen to original narration</summary><p className="mb-2 text-xs text-gray-500 dark:text-gray-400">Before audio edits. Use Preview scene to hear the current mix.</p><audio aria-label={`Scene ${index + 1} narration`} controls preload="none" key={scene.voiceover || scene.file} className="h-10 w-full"><source src={MEDIA_URL + (scene.voiceover || scene.file)} /></audio></details> : <p className="mt-4 text-xs text-gray-400">No narration yet</p>)}
            <div className="mt-4"><SceneAudio scene={scene} index={index} nextScene={nextScene} disabled={timingDisabled} onSaved={setUpdated} /></div>
                </TabPanel>
                <TabPanel unmount={false}>
                  <h3 className="mb-4 text-sm font-semibold">Captions, overlays &amp; motion</h3>
            <div aria-label="Scene editing tools" className="flex flex-wrap items-center gap-2">{!diagram && <SceneOverlays scene={scene} index={index} disabled={timingDisabled} onSaved={setUpdated} videoFormat={video_format} />}<SceneCaptions scene={scene} index={index} disabled={timingDisabled} onSaved={setUpdated} videoFormat={video_format} />{onMotion && <SceneMotion fps={exportFps} scene={scene} index={index} disabled={motionDisabled} saving={motionSaving} onChange={onMotion} videoFormat={video_format} />}</div>
                </TabPanel>
                {(onTiming || transitionControl) && <TabPanel unmount={false}>
                  <section aria-label="Quick scene timing" className="space-y-5">
                    {onTiming && <div><h3 className="text-sm font-semibold">Scene timing</h3><SceneTiming manual={manual} scene={scene} index={index} disabled={timingDisabled} saving={timingSaving} onChange={onTiming} /></div>}
                    {transitionControl && <div><h3 className="mb-3 text-sm font-semibold">Transition to next scene</h3>{transitionControl}</div>}
                  </section>
                </TabPanel>}
              </TabPanels>
            </TabGroup>
          </aside>
        </div>
      </article>
    </>
  );
};
