import { videoFrameSize } from "../utils/videoFormats";
import { useState } from "react";
import { OverlayLayer } from "./OverlayLayer";

// Show the completed diagram initially so an unrevealed first frame never looks empty.
export function SceneDiagramPreview({ scene, videoFormat, controls = false }) {
  const duration = scene.timing?.duration || 5;
  const end = Math.max(0, duration - .01);
  const [time, setTime] = useState(null);
  const frameSize = videoFrameSize(videoFormat);
  return <div className={controls ? "" : "relative flex h-full w-full items-center justify-center"}>
    <div className={`relative overflow-hidden rounded-xl bg-[#0f172a] ${controls ? "mx-auto max-h-[420px] max-w-full" : "h-full max-w-full"}`} style={controls ? { aspectRatio: `${frameSize[0]} / ${frameSize[1]}`, width: videoFormat === "PORTRAIT" ? 236 : videoFormat === "SQUARE" ? 420 : "100%" } : { aspectRatio: `${frameSize[0]} / ${frameSize[1]}` }}>
      <OverlayLayer overlays={scene.overlays} logo={scene.overlay_logo} time={Math.min(time ?? end, end)} duration={duration} frameSize={frameSize} />
    </div>
    {controls && <label className="mt-3 block text-xs text-gray-500 dark:text-gray-400">Preview animation
      <input aria-label="Diagram preview time" type="range" min="0" max={end} step="any" value={Math.min(time ?? end, end)} onChange={event => setTime(Number(event.target.value))} className="mt-2 block w-full accent-blue-600" />
    </label>}
  </div>;
}
