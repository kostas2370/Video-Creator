import { useRef, useState } from "react";
import { Dialog, DialogBackdrop, DialogPanel, DialogTitle } from "@headlessui/react";
import { HiOutlineFilm, HiOutlineXMark, HiOutlineArrowTopRightOnSquare, HiOutlineArrowPath } from "react-icons/hi2";

function VideoPlayer({ output, title }) {
  const player = useRef(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  return <div className="relative overflow-hidden rounded-xl bg-black shadow-inner">
    <video ref={player} src={output} controls playsInline preload="metadata" aria-label={title}
      className="max-h-[55vh] w-full object-contain"
      onLoadStart={() => setLoading(true)} onLoadedMetadata={() => setLoading(false)}
      onError={() => { setFailed(true); setLoading(false); }}>
      Your browser does not support video playback.
    </video>
    {loading && !failed ? <p role="status" className="pointer-events-none absolute left-3 top-3 rounded-full bg-black/70 px-3 py-1.5 text-xs text-white">Loading video…</p> : null}
    {failed ? <div role="alert" className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-gray-950 p-5 text-center text-white">
      <HiOutlineFilm aria-hidden="true" className="h-9 w-9 text-gray-500" />
      <p className="text-sm">This video could not be played. Try again or open the video directly.</p>
      <button type="button" onClick={() => { setFailed(false); setLoading(true); player.current?.load(); }} className="inline-flex items-center gap-2 rounded-lg border border-gray-600 px-4 py-2 text-sm font-medium hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"><HiOutlineArrowPath aria-hidden="true" className="h-4 w-4" />Try again</button>
    </div> : null}
  </div>;
}

function Script({ answer }) {
  let script = answer;
  if (typeof script === "string") {
    try { script = JSON.parse(script); } catch { /* Plain-text scripts are also supported. */ }
  }
  if (Array.isArray(script?.scenes)) {
    return <ol className="space-y-4">{script.scenes.map((scene, index) => <li key={index} className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">Scene {index + 1}</p>
      {(Array.isArray(scene.sentences) ? scene.sentences : []).map((line, lineIndex) => <div key={lineIndex} className={lineIndex ? "mt-4 border-t border-gray-100 pt-4 dark:border-gray-700" : ""}>
        {line.sentence ? <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-800 dark:text-gray-200">{line.sentence}</p> : null}
        {line.image_description ? <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-gray-500 dark:text-gray-400"><span className="font-medium">Visual: </span>{line.image_description}</p> : null}
      </div>)}
    </li>)}</ol>;
  }
  return <p className="whitespace-pre-wrap break-words text-sm leading-relaxed text-gray-600 dark:text-gray-300">{typeof script === "string" ? script : JSON.stringify(script, null, 2)}</p>;
}

export const VideoInfoModal = ({ showModal, setShowModal, videoInfo }) => {
  if (!showModal || !videoInfo) return null;
  const title = videoInfo.title || "Untitled video";
  const prompt = typeof videoInfo.prompt === "string" ? videoInfo.prompt : videoInfo.prompt?.prompt;
  return <Dialog open={showModal} onClose={() => setShowModal(false)} className="relative z-50">
    <DialogBackdrop transition className="fixed inset-0 bg-gray-950/70 backdrop-blur-sm transition duration-200 data-[closed]:opacity-0 motion-reduce:transition-none" />
    <div className="fixed inset-0 flex items-center justify-center p-3 sm:p-6">
      <DialogPanel transition className="flex max-h-[calc(100dvh-1.5rem)] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl transition duration-200 data-[closed]:scale-95 data-[closed]:opacity-0 motion-reduce:transition-none dark:border-gray-700 dark:bg-gray-900 sm:max-h-[calc(100dvh-3rem)]">
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-gray-100 px-5 py-4 dark:border-gray-800 sm:px-6">
          <div className="min-w-0"><p className="mb-1 text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-400">{videoInfo.output ? "Video preview" : "Video details"}</p><DialogTitle className="break-words text-lg font-semibold text-gray-900 dark:text-white sm:text-xl">{title}</DialogTitle></div>
          <button type="button" data-autofocus aria-label="Close video preview" onClick={() => setShowModal(false)} className="shrink-0 rounded-full p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:hover:bg-gray-800 dark:hover:text-white"><HiOutlineXMark aria-hidden="true" className="h-5 w-5" /></button>
        </header>
        <div className="min-h-0 overflow-y-auto p-4 sm:p-6">
          {videoInfo.output ? <VideoPlayer key={videoInfo.output} output={videoInfo.output} title={title} /> : <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-gray-300 bg-gray-50 px-6 py-10 text-center dark:border-gray-700 dark:bg-gray-800/50"><HiOutlineFilm aria-hidden="true" className="h-10 w-10 text-gray-400" /><p className="text-sm font-medium text-gray-600 dark:text-gray-300">No rendered video yet</p><p className="text-xs text-gray-500 dark:text-gray-400">Render this video from the editor to watch it here.</p></div>}
          <div className="mt-5 space-y-3">
            {prompt ? <details className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/50"><summary className="cursor-pointer text-sm font-semibold text-gray-900 dark:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">Original prompt</summary><p className="mt-3 whitespace-pre-wrap break-words text-sm leading-relaxed text-gray-600 dark:text-gray-300">{prompt}</p></details> : null}
            {videoInfo.gpt_answer ? <details className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/50"><summary className="cursor-pointer text-sm font-semibold text-gray-900 dark:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">Scene script</summary><div className="mt-4"><Script answer={videoInfo.gpt_answer} /></div></details> : null}
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-1 text-xs"><span className="font-medium text-gray-500 dark:text-gray-400">Background music</span><span className="break-all text-gray-600 dark:text-gray-300">{videoInfo.music || "No background music"}</span></div>
          </div>
        </div>
        <footer className="flex shrink-0 flex-wrap items-center justify-end gap-3 border-t border-gray-100 px-5 py-4 dark:border-gray-800 sm:px-6">
          <button type="button" onClick={() => setShowModal(false)} className="rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800">Close</button>
          {videoInfo.output ? <a href={videoInfo.output} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900">Open video<HiOutlineArrowTopRightOnSquare aria-hidden="true" className="h-4 w-4" /><span className="sr-only"> in a new tab</span></a> : null}
        </footer>
      </DialogPanel>
    </div>
  </Dialog>;
};
