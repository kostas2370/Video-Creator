import { useState } from "react";
import { searchMusicWithAI, importSearchMusic, recommendMusicWithAI } from "../api/apiService";
import { EditorDialog, editorButton, editorInput } from "./ui/EditorDialog";
import { mediaUrl } from "../utils/media";

export function AIMusicPicker({ open, onClose, videoId, prompt = "", genre = "", gptModel = "", onSelected, onSaved }) {
  const [preferences, setPreferences] = useState("");
  const [result, setResult] = useState(null), [preview, setPreview] = useState(null);
  const [pending, setPending] = useState(null), [error, setError] = useState("");
  const busy = pending !== null;
  const findMusic = async (recommendOnly = false) => {
    if (busy) return;
    setPending(recommendOnly ? "recommend" : "search"); setError("");
    if (!recommendOnly) setPreview(null);
    try {
      const response = await (recommendOnly ? recommendMusicWithAI : searchMusicWithAI)({ ...(videoId ? { video_id: videoId } : { prompt, genre }), gpt_model: gptModel, preferences });
      if (!response.ok) throw new Error(response.message || "Could not prepare music suggestions.");
      if (recommendOnly) setPreferences(response.data.preferences);
      else setResult(response.data);
    } catch (reason) { setError(reason.message); }
    finally { setPending(null); }
  };
  const choose = async track => {
    if (busy) return;
    setPending(track.key); setError("");
    try {
      if (videoId) {
        const response = await importSearchMusic(videoId, track.key);
        if (!response.ok) throw new Error(response.message || "Could not add this music.");
        onSaved?.();
      } else onSelected(track);
      setPreview(null); onClose();
    } catch (reason) { setError(reason.message); }
    finally { setPending(null); }
  };
  return <EditorDialog open={open} onClose={() => { setPreview(null); onClose(); }} title="AI search YouTube" description="Describe the sound you want. AI creates a music brief and ranks tracks from your general library and YouTube." busy={busy} maxWidth="max-w-3xl">
    <form onSubmit={event => { event.preventDefault(); findMusic(); }} className="space-y-3"><label className="block text-sm font-medium">Music preferences (optional)<input value={preferences} onChange={event => setPreferences(event.target.value)} disabled={busy} maxLength={500} placeholder="Soft piano, curious mood, no vocals…" className={`${editorInput} mt-2`} /></label><button type="button" onClick={() => findMusic(true)} disabled={busy} className="text-sm font-medium text-blue-600 underline disabled:opacity-40">{pending === "recommend" ? "Recommending…" : "Recommend"}</button><p className="text-xs text-gray-500">Uses your connected script model and the server's YouTube API key.</p><button className={editorButton} disabled={busy}>{pending === "search" ? "Finding music…" : "Find music"}</button></form>
    {error && <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-300">{error}</p>}
    {result && <div className="mt-5 space-y-4"><p className="rounded-xl border border-blue-400/30 p-3 text-sm text-blue-700 dark:text-blue-200">{result.brief.mood} · {result.brief.instruments} · {result.brief.tempo}</p><p className="text-xs text-gray-500">Matches use titles and tags. Preview before choosing. YouTube tracks declare Creative Commons; source and credit details are shown below.</p>{!result.tracks.length && <p>No matching tracks found. Try different preferences.</p>}{result.tracks.map(track => <article key={track.key} className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"><h3 className="text-sm font-semibold">{track.title}</h3><p className="mt-1 text-xs text-gray-500">{track.file ? "General library" : track.channel || "YouTube"} · {Math.round(track.duration || 0)}s</p><p className="mt-2 text-sm">{track.reason}</p><details className="mt-2 text-xs text-gray-500"><summary className="cursor-pointer">Source and attribution</summary><p className="mt-2 break-words">{track.attribution}</p><a href={track.source_url} target="_blank" rel="noreferrer" className="mr-3 underline">Source</a><a href={track.license_url} target="_blank" rel="noreferrer" className="underline">License information</a></details><div className="mt-3 flex flex-wrap gap-3"><button type="button" disabled={busy} onClick={() => setPreview(preview === track.key ? null : track.key)} className="text-sm text-blue-600 underline">{preview === track.key ? "Close preview" : "Preview"}</button><button type="button" disabled={busy} onClick={() => choose(track)} className={editorButton}>{pending === track.key ? "Adding music…" : "Use this music"}</button></div>{preview === track.key && (track.file ? <audio className="mt-3 w-full" src={mediaUrl(track.file)} controls preload="metadata" /> : track.key.startsWith("ai:") ? <iframe className="mt-3 aspect-video w-full rounded-lg" title={`Preview ${track.title}`} src={`https://www.youtube-nocookie.com/embed/${track.key.slice(3)}`} allow="encrypted-media; picture-in-picture" allowFullScreen /> : <p className="mt-3 text-xs">Open the source link to preview this track.</p>)}</article>)}</div>}
  </EditorDialog>;
}
