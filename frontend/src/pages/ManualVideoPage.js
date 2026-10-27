import { videoFormats } from "../utils/videoFormats";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { HiOutlineFilm } from "react-icons/hi2";
import { createManualVideo } from "../api/apiService";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";
import { editorInput, editorButton } from "../components/ui/EditorDialog";

export function ManualVideo() {
  useAxiosPrivate();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [format, setFormat] = useState("LANDSCAPE");
  const [subtitles, setSubtitles] = useState(true);
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  const create = async event => {
    event.preventDefault();
    if (busy || !title.trim()) return;
    setBusy(true); setError("");
    try {
      const response = await createManualVideo({ title: title.trim(), video_format: format, subtitles });
      if (!response.ok) throw new Error(response.message || "Could not create your project. Try again.");
      navigate(`/videos/${response.data.id}/`);
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  };
  return <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
    <header className="mb-8"><HiOutlineFilm aria-hidden="true" className="mb-4 h-10 w-10 text-blue-600" /><h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Make a video your way</h1><p className="mt-3 max-w-2xl leading-relaxed text-gray-500 dark:text-gray-400">Start with an empty project. Upload your photos and clips, arrange scenes, record your voice, and add music. No AI or API keys required.</p></header>
    <form onSubmit={create} className="rounded-2xl border border-gray-200 bg-white p-4 sm:p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <fieldset disabled={busy} className="space-y-6">
        <label className="block text-sm font-semibold" htmlFor="manual-title">Project title<input id="manual-title" required maxLength={50} value={title} onChange={event => setTitle(event.target.value)} className={`${editorInput} mt-2`} placeholder="My next video" autoFocus /></label>
        <fieldset><legend className="mb-3 text-sm font-semibold">Video format</legend><div className="grid grid-cols-1 gap-3 sm:grid-cols-3">{videoFormats.map(({ value, label, ratio }) => <label key={value} className={`cursor-pointer rounded-xl border p-4 text-center focus-within:ring-2 focus-within:ring-blue-500 ${format === value ? "border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-200" : "border-gray-200 dark:border-gray-600"}`}><input type="radio" name="manual-format" className="sr-only" checked={format === value} onChange={() => setFormat(value)} /><span className="block text-sm font-semibold">{label}</span><span className="mt-1 block text-xs text-gray-400">{ratio}</span></label>)}</div></fieldset>
        <label className="flex items-center gap-3 text-sm"><input type="checkbox" checked={subtitles} onChange={event => setSubtitles(event.target.checked)} className="accent-blue-600" />Show the caption text I add to each scene</label>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">{error}</p>}
        <button type="submit" disabled={busy || !title.trim()} className={editorButton}>{busy ? "Creating project…" : "Create empty project"}</button>
      </fieldset>
    </form>
    <p className="mt-5 text-sm text-gray-500 dark:text-gray-400">Add images, videos, captions, music, and voiceovers in the editor. Adjust scene duration, ordering, and transitions before exporting.</p>
  </main>;
}
