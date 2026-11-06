import React, { useEffect, useRef, useState } from "react";
import { toast } from "react-toastify";
import { getVideo, renderVideo } from "../api/apiService";
import { waitForVideo } from "../api/waitForVideo";
import { GiProcessor } from "react-icons/gi";
import { EditorDialog, editorInput, editorButton, editorSecondaryButton } from "./ui/EditorDialog";

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

  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title="Export video" description="Choose the quality and frame rate for your finished video." icon={GiProcessor} maxWidth="max-w-2xl" footer={<div className="flex flex-wrap items-center justify-between gap-3">
    <p className="min-w-0 flex-1 truncate text-xs text-gray-500 dark:text-gray-400">{name}</p>
    <div className="flex gap-2"><button type="button" onClick={() => setShowModal(false)} className={editorSecondaryButton}>Cancel</button><button type="button" disabled={audioCheck.loading} onClick={RenderClick} className={editorButton}>{audioCheck.scenes.length ? "Render anyway" : "Export video"}</button></div>
  </div>}>
    <div className="space-y-6">
      <fieldset disabled={audioCheck.loading}>
        <legend className="mb-3 text-sm font-semibold">Export quality</legend>
        <div className="grid gap-3 sm:grid-cols-3">{[
          ["DRAFT", "Draft", "A quick review", "Faster encoding with more compression."],
          ["STANDARD", "Standard", "Balanced", "A balance of detail, time and file size."],
          ["HIGH", "High", "Best detail", "More source detail; longer encoding and larger files."],
        ].map(([value, label, detail, help]) => <label key={value} className={`cursor-pointer rounded-2xl border p-4 transition-colors focus-within:ring-2 focus-within:ring-blue-500 ${exportPreset === value ? "border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-500/10" : "border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900"}`}>
          <span className="flex items-center justify-between gap-2 text-sm font-semibold">{label}<input type="radio" name="export-quality" value={value} checked={exportPreset === value} onChange={() => setExportPreset(value)} className="accent-blue-600" /></span><span className="mt-3 block text-xs font-semibold text-blue-600 dark:text-blue-300">{detail}</span><span className="mt-2 block text-xs leading-relaxed text-gray-500 dark:text-gray-400">{help}</span>
        </label>)}</div>
      </fieldset>
      <div className="rounded-2xl border border-gray-200 p-4 dark:border-gray-700"><label className="block text-sm font-semibold" htmlFor="export-fps">Frame rate</label><select id="export-fps" value={exportFps} disabled={audioCheck.loading} onChange={event => setExportFps(Number(event.target.value))} aria-describedby="export-fps-help" className={`${editorInput} mt-3`}><option value={24}>24 fps · Cinematic</option><option value={30}>30 fps · Smoother motion</option></select><p id="export-fps-help" className="mt-3 text-xs leading-relaxed text-gray-500 dark:text-gray-400">30 fps gives image motion more frames and may take longer to render. It does not add detail to source clips. Your project dimensions stay the same.</p></div>
      <div className="min-h-6">
        {audioCheck.loading && <p role="status" className="text-sm text-gray-500">Checking narration…</p>}
        {audioCheck.scenes.length > 0 && <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200"><p className="font-semibold">Missing narration in {audioCheck.scenes.length === 1 ? "scene" : "scenes"} {audioCheck.scenes.join(", ")}</p><p className="mt-2 leading-relaxed">These scenes will render without narration. Cancel to retry audio in the editor, or continue with the available audio.</p></div>}
        {audioCheck.failed && <p role="status" className="text-sm text-amber-700 dark:text-amber-300">Narration could not be checked. You can still render, or cancel and review the scenes.</p>}
      </div>
    </div>
  </EditorDialog>;
}
