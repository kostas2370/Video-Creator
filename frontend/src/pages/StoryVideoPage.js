import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { HiOutlineMicrophone, HiOutlineArrowUpTray, HiOutlineSparkles } from "react-icons/hi2";
import { toast } from "react-toastify";
import { VideoCreationMode } from "../components/VideoCreationMode";
import { MoreAssetOptions } from "../components/ui/MoreAssetOptions";
import { editorInput, editorButton } from "../components/ui/EditorDialog";
import { createStoryVideo, draftStory, getVoices } from "../api/apiService";
import { CaptionLayer } from "../components/CaptionLayer";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";
import { useAssetOptions } from "../hooks/useAssetOptions";
import { useObjectUrl } from "../hooks/useObjectUrl";

const defaultStoryPrompt = "Write an original fictional story for narration over gameplay. Choose an intriguing everyday mystery, or use my topic below.\n\nUse first person and a natural, conversational tone. Start immediately with a strong hook, build suspense, and finish with a satisfying twist or payoff. Aim for 120–180 words and fewer than 1,800 characters. Write only the words the narrator should say, with no headings, hashtags, or scene directions. Write in English.\n\nMy topic: surprise me.";

export function StoryVideo() {
  useAxiosPrivate();
  const navigate = useNavigate();
  const voices = useAssetOptions(getVoices);
  const [title, setTitle] = useState("");
  const [story, setStory] = useState("");
  const [idea, setIdea] = useState(defaultStoryPrompt);
  const [generating, setGenerating] = useState(false);
  const [gameplay, setGameplay] = useState(null);
  const [voice, setVoice] = useState("");
  const [subtitles, setSubtitles] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const gameplayUrl = useObjectUrl(gameplay);
  const words = story.trim().split(/\s+/).filter(Boolean).length;
  const ready = title.trim() && story.trim() && gameplay && voice && !busy && !generating;

  const generateStory = async () => {
    if (!idea.trim() || generating || busy) return;
    setGenerating(true); setError("");
    try {
      const response = await draftStory({ prompt: idea.trim() });
      if (!response.ok) throw new Error(response.message || "Could not generate a story. Try again.");
      setStory(response.data.story);
      setTitle(current => current.trim() ? current : response.data.title);
    } catch (reason) { setError(reason.message); }
    finally { setGenerating(false); }
  };

  const chooseGameplay = event => {
    const file = event.target.files?.[0];
    setError("");
    setGameplay(null);
    if (!file) return;
    if (file.size > 100 * 1024 * 1024) {
      setError("Choose a gameplay clip smaller than 100 MB.");
      event.target.value = "";
      return;
    }
    setGameplay(file);
  };
  const create = async event => {
    event.preventDefault();
    if (!ready) return;
    setBusy(true); setError("");
    const data = new FormData();
    data.append("title", title.trim());
    data.append("story", story.trim());
    data.append("gameplay", gameplay);
    data.append("voice_id", voice);
    data.append("subtitles", String(subtitles));
    try {
      const response = await createStoryVideo(data);
      if (!response.ok) throw new Error(response.message || "Could not create your story video. Try again.");
      if (response.data.warning) toast.warning(response.data.warning);
      navigate(`/videos/${response.data.id}/`);
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  };

  return <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
    <VideoCreationMode />
    <header className="mb-8 max-w-2xl">
      <span className="mb-4 inline-flex items-center gap-2 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"><HiOutlineMicrophone aria-hidden="true" />Made for short stories</span>
      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">One story. Nonstop gameplay.</h1>
      <p className="mt-3 leading-relaxed text-gray-500 dark:text-gray-400">Give viewers something to watch while your narrator tells the story. Add your gameplay, paste the words, and make a vertical video for TikTok, Reels, or Shorts.</p>
    </header>
    <form onSubmit={create} className="grid items-start gap-8 lg:grid-cols-[1fr_300px]">
      <fieldset disabled={busy || generating} className="min-w-0 space-y-6 rounded-2xl border border-gray-200 bg-white p-4 sm:p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <label className="block text-sm font-semibold" htmlFor="story-title">Video title<input id="story-title" required maxLength={50} value={title} onChange={event => setTitle(event.target.value)} className={`${editorInput} mt-2`} placeholder="The message I should have ignored" /></label>
        <div>
          <details className="mb-5 rounded-xl border border-blue-200 bg-blue-50/60 p-4 dark:border-blue-800 dark:bg-blue-950/20">
            <summary className="cursor-pointer rounded text-sm font-semibold text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-300">Need a story? Write one with AI</summary>
            <div className="mt-4">
            <label className="block text-sm font-semibold" htmlFor="story-idea">Story prompt</label>
            <p className="mt-1 text-xs leading-relaxed text-gray-500 dark:text-gray-400">The writing instructions are yours to edit. Change the topic, tone, length, language, or ending before generating.</p>
            <textarea id="story-idea" maxLength={2000} rows={7} value={idea} onChange={event => setIdea(event.target.value)} className={`${editorInput} mt-2`} placeholder="Describe your story and how you want it written…" aria-describedby="story-generate-help" />
            <button type="button" onClick={generateStory} disabled={!idea.trim() || generating || busy} className="mt-3 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"><HiOutlineSparkles aria-hidden="true" />{generating ? "Writing your story…" : story.trim() ? "Generate another story" : "Generate story"}</button>
            <p id="story-generate-help" role="status" className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">{generating ? "Writing a draft using your prompt…" : `Uses your configured AI text model. ${story.trim() ? "A new draft replaces the story below. " : ""}Review and edit it before creating your video.`}</p>
            </div>
          </details>
          <label className="block text-sm font-semibold" htmlFor="story-script">Your story</label>
          <p id="story-help" className="mt-1 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Paste the exact words the narrator should say. Start with a hook that makes people want to hear the rest.</p>
          <textarea id="story-script" required maxLength={2000} rows={9} value={story} onChange={event => setStory(event.target.value)} aria-describedby="story-help story-length" className={`${editorInput} mt-3`} placeholder="I thought it was just another wrong number. Then they sent a photo of my front door…" />
          <p id="story-length" className="mt-2 text-xs text-gray-500 dark:text-gray-400">{story.length}/2,000 characters{words > 0 ? ` · About ${Math.max(1, Math.round(words / 2.5))} seconds of narration` : ""}</p>
        </div>
        <div>
          <label htmlFor="story-gameplay" className="mb-2 block text-sm font-semibold">Background gameplay</label>
          <div className="rounded-xl border border-dashed border-gray-300 p-4 dark:border-gray-600">
            <HiOutlineArrowUpTray aria-hidden="true" className="mb-2 h-5 w-5 text-blue-500" />
            <input id="story-gameplay" type="file" required accept=".mp4,.mov,.webm,.avi,.m4v" onChange={chooseGameplay} className="w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:font-semibold file:text-blue-700 dark:file:bg-gray-700 dark:file:text-blue-300" aria-describedby="gameplay-help" />
            <p id="gameplay-help" className="mt-3 text-xs leading-relaxed text-gray-500 dark:text-gray-400">Upload your own recording or a clip you have permission to use, such as endless-runner gameplay or parkour. Up to 100 MB / 15 minutes. Portrait footage works best; other clips are cropped to fill the frame.</p>
          </div>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Gameplay loops to match the narration. Its original sound is muted.</p>
        </div>
        <div>
          <label htmlFor="story-voice" className="mb-2 block text-sm font-semibold">Narrator</label>
          <select id="story-voice" required value={voice} onChange={event => setVoice(event.target.value)} className={editorInput}>
            <option value="">{voices.loading ? "Loading voices…" : "Choose a voice"}</option>
            {voices.items.map(item => <option key={item.id} value={item.id}>{item.name} · {item.provider}</option>)}
          </select>
          <MoreAssetOptions options={voices} label="voices" />
          {!voices.loading && !voices.items.length && !voices.failed && <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Connect a voice provider in <Link to="/api-keys/" className="text-blue-600 underline dark:text-blue-400">API keys</Link> to add narration.</p>}
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Uses your selected voice provider. No AI images or video generation needed.</p>
        </div>
        <label className="flex items-center gap-3 text-sm"><input type="checkbox" checked={subtitles} onChange={event => setSubtitles(event.target.checked)} className="accent-blue-600" />Add TikTok captions with word highlights</label>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">{error}</p>}
        <button type="submit" disabled={!ready} className={editorButton}>{busy ? "Uploading and preparing narration…" : "Create story video"}</button>
        <p className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">Review the narration and captions in the editor, then render and download your video. Caption timing is estimated from the narration.</p>
      </fieldset>
      <aside className="mx-auto w-full max-w-[300px] lg:sticky lg:top-6">
        <div className="relative aspect-[9/16] overflow-hidden rounded-3xl border border-gray-700 bg-gray-950 shadow-xl">
          {gameplayUrl ? <video key={gameplayUrl} src={gameplayUrl} controls muted loop playsInline preload="metadata" className="h-full w-full object-cover" /> : <div className="flex h-full flex-col items-center justify-center gap-3 px-8 text-center text-gray-400"><HiOutlineArrowUpTray aria-hidden="true" className="h-8 w-8 text-blue-400" /><p className="text-sm">Your gameplay goes here</p><p className="text-xs leading-relaxed">A looping background for the story they can’t stop listening to.</p></div>}
          {subtitles && <CaptionLayer style="TIKTOK" cue={{ text: story.trim() ? story.trim().split(/\s+/).slice(0, 4).join(" ") : "It started with\none message…", active_word: 2 }} />}
          <span className="pointer-events-none absolute left-4 top-4 rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-white">9:16 · Portrait</span>
        </div>
        <p className="mt-3 text-center text-xs text-gray-500 dark:text-gray-400">Layout preview · Narration is created next</p>
      </aside>
    </form>
  </main>;
}
