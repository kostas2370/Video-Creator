import React, { useState, useEffect } from "react";
import { getIntro, getOutro, getAvatars, updateVideo } from "../api/apiService";
import { transitionDurations, transitionStyles } from "./SceneTransition";
import { AssetDropBox } from "./ui/assetDropBox";
import { toast } from "react-toastify";
import { CloseModalButton } from "./ui/CloseModalButton";
import { RiSettings3Line, RiMovieLine, RiUser3Line } from "react-icons/ri";

const positions = [
  ["left,top", "Top left"],
  ["right,top", "Top right"],
  ["left,bottom", "Bottom left"],
  ["right,bottom", "Bottom right"],
];
const videoFormats = [
  { value: "LANDSCAPE", label: "Landscape", ratio: "16:9", shape: "w-12 aspect-video" },
  { value: "PORTRAIT", label: "Portrait", ratio: "9:16", shape: "h-10 aspect-[9/16]" },
  { value: "SQUARE", label: "Square", ratio: "1:1", shape: "h-9 aspect-square" },
];
const platforms = [
  { value: "GENERAL", label: "General" },
  { value: "TIKTOK", label: "TikTok" },
];

const sectionTitle = "mb-1 text-sm font-semibold text-gray-900 dark:text-white";
const sectionDescription = "text-xs leading-relaxed text-gray-500 dark:text-gray-400";
const normalizeAvatarPosition = (position) => {
  const parts = String(position || "").split(",");
  const horizontal = parts.find((part) => part === "left" || part === "right");
  const vertical = parts.find((part) => part === "top" || part === "bottom");
  const normalized = `${horizontal || "right"},${vertical || "top"}`;
  return positions.some(([value]) => value === normalized) ? normalized : "right,top";
};

export const VideoConfigModal = ({ showModal, setShowModal, info, onSaved }) => {
  const [avatars, setAvatars] = useState([]);
  const [avatar, setAvatar] = useState("");
  const [intros, setIntros] = useState([]);
  const [outros, setOutros] = useState([]);
  const [title, setTitle] = useState("");
  const [intro, setIntro] = useState("");
  const [outro, setOutro] = useState("");
  const [subtitles, setSubtitles] = useState(false);
  const [avatarPosition, setAvatarPosition] = useState("right,top");
  const [platform, setPlatform] = useState("GENERAL");
  const [videoFormat, setVideoFormat] = useState("LANDSCAPE");
  const [selectedIntroFile, setSelectedIntroFile] = useState("");
  const [selectedOutroFile, setSelectedOutroFile] = useState("");
  const [selectedAvatarFile, setSelectedAvatarFile] = useState("");
  const [transitionDefault, setTransitionDefault] = useState("FADE");
  const [transitionDuration, setTransitionDuration] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([getAvatars(), getIntro(), getOutro()]).then(([avatarResult, introResult, outroResult]) => {
      if (!active) return;
      setAvatars(Array.isArray(avatarResult.data) ? avatarResult.data : []);
      setIntros(Array.isArray(introResult.data) ? introResult.data : []);
      setOutros(Array.isArray(outroResult.data) ? outroResult.data : []);
    }).catch((error) => console.error("Error fetching video settings:", error));
    return () => { active = false; };
  }, []);

  useEffect(() => setTitle(info?.title || ""), [info?.title]);
  useEffect(() => {
    setIntro(info?.intro ?? "");
    setSelectedIntroFile(intros.find((item) => String(item.id) === String(info?.intro))?.file || "");
  }, [info?.intro, intros]);
  useEffect(() => {
    setOutro(info?.outro ?? "");
    setSelectedOutroFile(outros.find((item) => String(item.id) === String(info?.outro))?.file || "");
  }, [info?.outro, outros]);
  useEffect(() => {
    setAvatar(info?.avatar ?? "");
    setSelectedAvatarFile(avatars.find((item) => String(item.id) === String(info?.avatar))?.file || "");
  }, [info?.avatar, avatars]);
  useEffect(() => {
    setAvatarPosition(normalizeAvatarPosition(info?.settings?.avatar_position));
    setPlatform(info?.settings?.platform || "GENERAL");
    setVideoFormat(info?.settings?.video_format || "LANDSCAPE");
    setSubtitles(info?.settings?.subtitles === true);
    setTransitionDefault(info?.settings?.transition_default || "FADE");
    setTransitionDuration(info?.settings?.transition_duration ?? "");
  }, [info?.settings]);

  const changePlatform = (value) => {
    setPlatform(value);
    if (value === "TIKTOK") {
      setVideoFormat("PORTRAIT");
      setSubtitles(true);
    }
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      const changes = {
        intro,
        outro,
        title,
        avatar,
        subtitles,
        platform,
        video_format: videoFormat,
        transition_default: transitionDefault,
        transition_duration: transitionDuration === "" ? null : Number(transitionDuration),
      };
      if (avatar) changes.avatar_position = normalizeAvatarPosition(avatarPosition);
      const { data: response } = await updateVideo(info.id, changes);
      if (response) {
        toast.success("Video settings saved");
        onSaved?.();
        setShowModal(false);
      }
    } finally {
      setSaving(false);
    }
  };

  if (!showModal) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-gray-950/55 p-3 backdrop-blur-sm sm:p-6" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowModal(false); }}>
      <section role="dialog" aria-modal="true" aria-labelledby="video-settings-title" className="my-auto flex max-h-[min(92vh,900px)] w-full max-w-2xl flex-col overflow-hidden rounded-3xl border border-white/20 bg-white shadow-2xl shadow-gray-950/30 dark:border-gray-700 dark:bg-gray-900">
        <header className="relative flex items-start gap-4 border-b border-gray-100 bg-gradient-to-br from-blue-50 via-white to-indigo-50 px-5 py-5 sm:px-7 sm:py-6 dark:border-gray-800 dark:from-blue-950/50 dark:via-gray-900 dark:to-indigo-950/40">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-blue-600 shadow-sm ring-1 ring-gray-200 dark:bg-gray-800 dark:text-blue-300 dark:ring-gray-700"><RiSettings3Line aria-hidden="true" className="h-5 w-5" /></span>
          <div className="min-w-0 flex-1 pr-8">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-blue-600 dark:text-blue-300">Video editor</p>
            <h2 id="video-settings-title" className="mt-1 text-xl font-bold tracking-tight text-gray-950 dark:text-white">Video settings</h2>
            <p className="mt-1 truncate text-sm text-gray-500 dark:text-gray-400">Customize {title || "your video"} before rendering.</p>
          </div>
          <CloseModalButton setShowModal={setShowModal} />
        </header>

        <form onSubmit={onSubmit} className="flex min-h-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 space-y-6 overflow-y-auto p-5 sm:p-7">
            <div>
              <label htmlFor="video-title" className="mb-2 block text-sm font-semibold text-gray-800 dark:text-gray-100">Video title</label>
              <input id="video-title" type="text" value={title} onChange={(event) => setTitle(event.target.value)} required maxLength={50} placeholder="Name your video" className="w-full rounded-xl border border-gray-200 bg-white px-3.5 py-3 text-sm text-gray-900 shadow-sm outline-none transition placeholder:text-gray-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 dark:border-gray-700 dark:bg-gray-800 dark:text-white" />
            </div>

            <section className="rounded-2xl border border-gray-200 bg-gray-50/70 p-4 sm:p-5 dark:border-gray-800 dark:bg-gray-800/40">
              <h3 className={sectionTitle}>Output format</h3>
              <p className={sectionDescription}>Choose a platform preset and frame for your next render.</p>
              <div role="radiogroup" aria-label="Target platform" className="mt-3 grid grid-cols-2 gap-2">
                {platforms.map((option) => <label key={option.value} className={`flex cursor-pointer items-center justify-center rounded-xl border p-2.5 text-sm font-medium transition focus-within:ring-2 focus-within:ring-blue-500 ${platform === option.value ? "border-blue-500 bg-blue-50 text-blue-700 ring-1 ring-blue-500/20 dark:border-blue-400 dark:bg-blue-400/10 dark:text-blue-200" : "border-gray-200 bg-white text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"}`}>
                  <input className="sr-only" type="radio" name="edit-platform" value={option.value} checked={platform === option.value} onChange={() => changePlatform(option.value)} />{option.label}
                </label>)}
              </div>
              {platform === "TIKTOK" && <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Places captions in a safer area. Switching here does not rewrite existing narration.</p>}
              <div role="radiogroup" aria-label="Output format" className="mt-4 grid grid-cols-3 gap-2">
                {videoFormats.map((option) => <label key={option.value} className={`flex cursor-pointer flex-col items-center gap-2 rounded-xl border p-3 text-center transition focus-within:ring-2 focus-within:ring-blue-500 ${videoFormat === option.value ? "border-blue-500 bg-blue-50 text-blue-700 ring-1 ring-blue-500/20 dark:border-blue-400 dark:bg-blue-400/10 dark:text-blue-200" : "border-gray-200 bg-white text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"}`}>
                  <input className="sr-only" type="radio" name="edit-video-format" value={option.value} checked={videoFormat === option.value} onChange={() => setVideoFormat(option.value)} />
                  <span className="flex h-10 items-center justify-center"><span aria-hidden="true" className={`${option.shape} rounded-[3px] border-2 ${videoFormat === option.value ? "border-blue-500 dark:border-blue-300" : "border-gray-400 dark:border-gray-500"}`} /></span>
                  <span><span className="block text-xs font-semibold">{option.label}</span><span className="mt-0.5 block text-[10px] text-gray-400">{option.ratio}</span></span>
                </label>)}
              </div>
            </section>

            <section className="rounded-2xl border border-gray-200 bg-gray-50/70 p-4 sm:p-5 dark:border-gray-800 dark:bg-gray-800/40">
              <h3 className={sectionTitle}>Scene transitions</h3>
              <p className={sectionDescription}>Set the default for this video. Individual scene overrides stay in place.</p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-200">Default transition
                  <select aria-label="Default transition" disabled={saving} className="mt-2 block w-full rounded-xl border border-gray-200 bg-white p-3 text-sm dark:border-gray-700 dark:bg-gray-800" value={transitionDefault} onChange={event => setTransitionDefault(event.target.value)}>{transitionStyles.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
                </label>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-200">Default duration
                  <select aria-label="Default transition duration" disabled={saving || transitionDefault === "CUT"} className="mt-2 block w-full rounded-xl border border-gray-200 bg-white p-3 text-sm disabled:opacity-50 dark:border-gray-700 dark:bg-gray-800" value={transitionDuration} onChange={event => setTransitionDuration(event.target.value)}><option value="">Automatic</option>{transitionDurations.map(value => <option key={value} value={value}>{value}s</option>)}</select>
                </label>
              </div>
              <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">Short scenes use a shorter transition when needed. Cross dissolve keeps dialogue timing intact.</p>
            </section>

            <section className="rounded-2xl border border-gray-200 bg-gray-50/70 p-4 sm:p-5 dark:border-gray-800 dark:bg-gray-800/40">
              <div className="mb-4 flex items-start gap-3"><span className="mt-0.5 text-blue-600 dark:text-blue-300"><RiMovieLine aria-hidden="true" className="h-5 w-5" /></span><div><h3 className={sectionTitle}>Opening and ending</h3><p className={sectionDescription}>Add reusable clips around your scenes.</p></div></div>
              <div className="grid gap-5 sm:grid-cols-2">
                <AssetDropBox value={intro} setValue={setIntro} setSelectedFile={setSelectedIntroFile} type="intro" items={intros} selectedFile={selectedIntroFile} />
                <AssetDropBox value={outro} setValue={setOutro} setSelectedFile={setSelectedOutroFile} type="outro" items={outros} selectedFile={selectedOutroFile} />
              </div>
            </section>

            <section className="rounded-2xl border border-gray-200 bg-gray-50/70 p-4 sm:p-5 dark:border-gray-800 dark:bg-gray-800/40">
              <div className="mb-4 flex items-start gap-3"><span className="mt-0.5 text-indigo-600 dark:text-indigo-300"><RiUser3Line aria-hidden="true" className="h-5 w-5" /></span><div><h3 className={sectionTitle}>Presenter and captions</h3><p className={sectionDescription}>Choose an avatar, its placement, and subtitle visibility.</p></div></div>
              <AssetDropBox value={avatar} setValue={setAvatar} setSelectedFile={setSelectedAvatarFile} type="avatar" items={avatars} selectedFile={selectedAvatarFile} />
              {avatar && (
                <fieldset className="mt-5">
                  <legend className="mb-2 text-sm font-semibold text-gray-800 dark:text-gray-100">Presenter position</legend>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {positions.map(([value, label]) => (
                      <label key={value} className={`flex cursor-pointer items-center justify-center rounded-xl border px-3 py-2.5 text-xs font-medium transition ${avatarPosition === value ? "border-blue-500 bg-blue-50 text-blue-700 ring-2 ring-blue-500/15 dark:border-blue-400 dark:bg-blue-400/10 dark:text-blue-200" : "border-gray-200 bg-white text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"}`}>
                        <input className="sr-only" type="radio" name="avatar-position" value={value} checked={avatarPosition === value} onChange={() => setAvatarPosition(value)} />
                        {label}
                      </label>
                    ))}
                  </div>
                </fieldset>
              )}
              <label htmlFor="video-subtitles" className="mt-5 flex cursor-pointer items-center gap-3 rounded-xl border border-gray-200 bg-white p-3.5 transition hover:border-blue-200 dark:border-gray-700 dark:bg-gray-800">
                <input type="checkbox" id="video-subtitles" checked={subtitles} onChange={(event) => setSubtitles(event.target.checked)} className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                <span aria-hidden="true" className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-50 text-xs font-bold tracking-tight text-blue-600 dark:bg-blue-400/10 dark:text-blue-300">CC</span>
                <span className="flex-1"><span className="block text-sm font-semibold text-gray-800 dark:text-gray-100">Subtitles</span><span className="mt-0.5 block text-xs text-gray-500 dark:text-gray-400">Show narration as on-screen captions.</span></span>
                <span className={`relative h-6 w-11 rounded-full transition ${subtitles ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"}`} aria-hidden="true"><span className={`absolute top-1 h-4 w-4 rounded-full bg-white shadow transition-all ${subtitles ? "left-6" : "left-1"}`} /></span>
              </label>
            </section>
          </div>

          <footer className="flex flex-col-reverse gap-2 border-t border-gray-100 bg-white px-5 py-4 sm:flex-row sm:justify-end sm:px-7 dark:border-gray-800 dark:bg-gray-900">
            <button type="button" disabled={saving} onClick={() => setShowModal(false)} className="rounded-xl px-4 py-3 text-sm font-semibold text-gray-600 transition hover:bg-gray-100 disabled:opacity-50 dark:text-gray-300 dark:hover:bg-gray-800">Cancel</button>
            <button type="submit" disabled={saving || !title.trim()} className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:opacity-50">{saving ? "Saving…" : "Save settings"}</button>
          </footer>
        </form>
      </section>
    </div>
  );
};
