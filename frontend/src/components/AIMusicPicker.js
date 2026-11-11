import { useState } from "react";
import { searchMusicWithAI, importSearchMusic } from "../api/apiService";
import { EditorDialog, editorButton, editorInput } from "./ui/EditorDialog";
import { mediaUrl } from "../utils/media";

function youtubeId(track) {
  try {
    const source = new URL(track.source_url);
    const id = source.searchParams.get("v");
    return /^[A-Za-z0-9_-]{11}$/.test(id || "") ? id : null;
  } catch { return null; }
}

export function AIMusicPicker({ open, onClose, videoId, prompt = "", genre = "", gptModel = "", onSelected, onSaved }) {
  const [preferences, setPreferences] = useState("");
  const [result, setResult] = useState(null), [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false), [adding, setAdding] = useState(null), [error, setError] = useState("");
  const search = async event => {
    event.preventDefault();
    if (busy || adding) return;
    setBusy(true); setError(""); setPreview(null);
    try {
      const response = await searchMusicWithAI({ ...(videoId ? { video_id: videoId } : { prompt, genre }), gpt_model: gptModel, preferences });
      if (!response.ok) throw new Error(response.message || "Could not search for music.");
      setResult(response.data);
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  };
  const choose = async track => {
    if (busy || adding) return;
    setAdding(track.key); setError("");
    try {
      if (videoId) {
        const response = await importSearchMusic(videoId, track.key);
        if (!response.ok) throw new Error(response.message || "Could not add this music.");
        onSaved?.();
      } else onSelected(track);
      setPreview(null); onClose();
    } catch (reason) { setError(reason.message); }
    finally { setAdding(null); }
  };
  return <EditorDialog open={open} onClose={() => { setPreview(null); onClose(); }} title="AI search YouTube" description="Describe the sound you want. AI creates a music brief and ranks tracks from your general library and YouTube." busy={busy || !!adding} maxWidth="max-w-3xl">
    <form onSubmit={search} className="space-y-3"><label className="block text-sm font-medium">Music preferences (optional)<input value={preferences} onChange={event => setPreferences(event.target.value)} disabled={busy || !!adding} maxLength={500} placeholder="Soft piano, curious mood, no vocals…" className={`${editorInput} mt-2`} /></label><p className="text-xs text-gray-500">Uses your connected script model and the server's YouTube API key.</p><button className={editorButton} disabled={busy || !!adding}>{busy ? "Finding music…" : "Find music"}</button></form>
    {error && <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-300">{error}</p>}
    {result && <div className="mt-5 space-y-4"><p className="rounded-xl border border-blue-400/30 p-3 text-sm text-blue-700 dark:text-blue-200">{result.brief.mood} · {result.brief.instruments} · {result.brief.tempo}</p><p className="text-xs text-gray-500">Matches use titles and tags. Preview before choosing. YouTube tracks declare Creative Commons; source and credit details are shown below.</p>{!result.tracks.length && <p>No matching tracks found. Try different preferences.</p>}{result.tracks.map(track => <article key={track.key} className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"><h3 className="text-sm font-semibold">{track.title}</h3><p className="mt-1 text-xs text-gray-500">{track.origin === "catalog" ? "General library" : track.channel || "YouTube"} · {Math.round(track.duration || 0)}s</p><p className="mt-2 text-sm">{track.reason}</p><details className="mt-2 text-xs text-gray-500"><summary className="cursor-pointer">Source and attribution</summary><p className="mt-2 break-words">{track.attribution}</p><a href={track.source_url} target="_blank" rel="noreferrer" className="mr-3 underline">Source</a><a href={track.license_url} target="_blank" rel="noreferrer" className="underline">License information</a></details><div className="mt-3 flex flex-wrap gap-3"><button type="button" disabled={busy || !!adding} onClick={() => setPreview(preview === track.key ? null : track.key)} className="text-sm text-blue-600 underline">{preview === track.key ? "Close preview" : "Preview"}</button><button type="button" disabled={busy || !!adding} onClick={() => choose(track)} className={editorButton}>{adding === track.key ? "Adding music…" : "Use this music"}</button></div>{preview === track.key && (track.origin === "catalog" && track.file ? <audio className="mt-3 w-full" src={mediaUrl(track.file)} controls preload="metadata" /> : youtubeId(track) ? <iframe className="mt-3 aspect-video w-full rounded-lg" title={`Preview ${track.title}`} src={`https://www.youtube-nocookie.com/embed/${youtubeId(track)}`} allow="encrypted-media; picture-in-picture" allowFullScreen /> : <p className="mt-3 text-xs">Open the source link to preview this track.</p>)}</article>)}</div>}
  </EditorDialog>;
}
