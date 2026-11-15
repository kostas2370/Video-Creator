import { useEffect, useRef, useState } from "react";
import { getVideo } from "../api/apiService";
import { subscribeUpdates } from "../api/subscribeUpdates";
import { libraryProgress } from "../utils/videoLibrary";

export function VideoLibraryProgress({ video, onFinished }) {
  const [detail, setDetail] = useState(video);
  const [unavailable, setUnavailable] = useState(false);
  const finished = useRef(onFinished);
  finished.current = onFinished;
  useEffect(() => subscribeUpdates(`videos/${encodeURIComponent(video.id)}/events/`, {
    load: () => getVideo(video.id, { notifyError: false }),
    onUpdate: next => {
      setDetail(next);
      setUnavailable(false);
      if (!["GENERATION", "RENDERING"].includes(next.status)) finished.current?.();
    },
    onError: () => setUnavailable(true),
  }), [video.id]);
  const progress = libraryProgress(detail);
  return <div className="mt-3 rounded-xl bg-blue-50/80 p-3 text-xs dark:bg-blue-500/10" aria-label={`Progress for ${video.title || "Untitled video"}`}>
    <p role="status" className="font-semibold text-blue-700 dark:text-blue-200">{progress.title}</p>
    {progress.steps.map(step => <div key={step.label} className="mt-2">
      <div className="mb-1 flex justify-between gap-2 text-[10px] text-gray-600 dark:text-gray-300"><span>{step.label}</span><span>{step.done} of {step.total} scenes</span></div>
      <progress aria-label={step.label} value={step.done} max={step.total} className="block h-1.5 w-full overflow-hidden rounded-full accent-blue-500" />
    </div>)}
    <p className="mt-2 text-[10px] leading-relaxed text-gray-500 dark:text-gray-400">{unavailable ? "Live updates are unavailable. Open the editor to check the latest status." : progress.description}</p>
  </div>;
}
