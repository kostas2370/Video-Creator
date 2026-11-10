import { StartingFrameOption } from "./StartingFrameOption";
import { NarrationSetup } from "./NarrationSetup";
import { GenerationModeSelect } from "./GenerationModeSelect";
import { VisualContinuity } from "./VisualContinuity";
import { videoFormats } from "../utils/videoFormats";
import { useAssetOptions } from "../hooks/useAssetOptions";
import { MoreAssetOptions } from "./ui/MoreAssetOptions";
import React, { useState, useEffect } from "react";
import { getIntro, getOutro, getAvatars, getVoices, updateVideo } from "../api/apiService";
import { defaultTransition, transitionDurations, transitionStyles } from "./SceneTransition";
import { AssetDropBox } from "./ui/assetDropBox";
import { toast } from "react-toastify";
import { RiSettings3Line, RiMovieLine, RiUser3Line } from "react-icons/ri";
import { CaptionStyleEditor } from "./CaptionStyleEditor";
import { EditorDialog, editorInput, editorButton, editorSecondaryButton } from "./ui/EditorDialog";

const positions = [
  ["left,top", "Top left"],
  ["right,top", "Top right"],
  ["left,bottom", "Bottom left"],
  ["right,bottom", "Bottom right"],
];
const platforms = [
  { value: "GENERAL", label: "General" },
  { value: "TIKTOK", label: "TikTok" },
];

const sectionTitle = "mb-1 text-sm font-semibold text-gray-900 dark:text-white";
const sectionDescription = "text-xs leading-relaxed text-gray-500 dark:text-gray-400";
const initialClipAudio = info => info?.settings?.video_audio_enabled ?? (info?.scenes?.length ? info.scenes.some(scene => scene.scene_image?.with_audio) : info?.settings?.narration === false);
const normalizeAvatarPosition = (position) => {
  const parts = String(position || "").split(",");
  const horizontal = parts.find((part) => part === "left" || part === "right");
  const vertical = parts.find((part) => part === "top" || part === "bottom");
  const normalized = `${horizontal || "right"},${vertical || "top"}`;
  return positions.some(([value]) => value === normalized) ? normalized : "right,top";
};

export const VideoConfigModal = ({ showModal, setShowModal, info, onSaved }) => {
  const avatarsOptions = useAssetOptions(getAvatars, showModal && info?.video_type !== "MANUAL");
  const avatars = avatarsOptions.items;
  const [avatar, setAvatar] = useState("");
  const [voice, setVoice] = useState("");
  const [narration, setNarration] = useState(true);
  const [narrationScenes, setNarrationScenes] = useState(null);
  const [writingNarration, setWritingNarration] = useState(false);
  const enablingNarration = info?.video_type !== "MANUAL" && info?.settings?.narration === false && narration;
  const needsNarrationReview = enablingNarration && !!info?.scenes?.length;
  const [videoAudioMode, setVideoAudioMode] = useState("AUTO");
  const [clipAudio, setClipAudio] = useState(false);
  const [clipAudioTouched, setClipAudioTouched] = useState(false);
  const [musicVolume, setMusicVolume] = useState(0.07);
  const voicesOptions = useAssetOptions(getVoices, showModal && !avatar && info?.video_type !== "MANUAL");
  const voices = voicesOptions.items;
  const introsOptions = useAssetOptions(getIntro, showModal);
  const intros = introsOptions.items;
  const outrosOptions = useAssetOptions(getOutro, showModal);
  const outros = outrosOptions.items;
  const [intro, setIntro] = useState("");
  const [outro, setOutro] = useState("");
  const [subtitles, setSubtitles] = useState(false);
  const [captionStyle, setCaptionStyle] = useState("CLASSIC");
  const [captionConfig, setCaptionConfig] = useState({});
  const [avatarPosition, setAvatarPosition] = useState("right,top");
  const [platform, setPlatform] = useState("GENERAL");
  const [videoFormat, setVideoFormat] = useState("LANDSCAPE");
  const [selectedIntroFile, setSelectedIntroFile] = useState("");
  const [selectedOutroFile, setSelectedOutroFile] = useState("");
  const [selectedAvatarFile, setSelectedAvatarFile] = useState("");
  const [transitionDefault, setTransitionDefault] = useState("FADE");
  const [transitionDuration, setTransitionDuration] = useState("");
  const [introTransition, setIntroTransition] = useState("DEFAULT");
  const [introTransitionDuration, setIntroTransitionDuration] = useState("");
  const [visualContinuity, setVisualContinuity] = useState("");
  const [reviewStartingFrames, setReviewStartingFrames] = useState(false);
  const [saving, setSaving] = useState(false);
  const busy = saving || writingNarration;
  const [generationMode, setGenerationMode] = useState("STANDARD");


  useEffect(() => {
    setSelectedIntroFile(intros.find((item) => String(item.id) === String(intro))?.file || "");
  }, [intro, intros]);
  useEffect(() => setIntro(info?.intro ?? ""), [info?.intro]);
  useEffect(() => {
    setSelectedOutroFile(outros.find((item) => String(item.id) === String(outro))?.file || "");
  }, [outro, outros]);
  useEffect(() => setOutro(info?.outro ?? ""), [info?.outro]);
  useEffect(() => {
    setSelectedAvatarFile(avatars.find((item) => String(item.id) === String(avatar))?.file || "");
  }, [avatar, avatars]);
  useEffect(() => setAvatar(info?.avatar ?? ""), [info?.avatar]);
  useEffect(() => setVoice(info?.voice_model ?? ""), [info?.voice_model]);
  useEffect(() => {
    setAvatarPosition(normalizeAvatarPosition(info?.settings?.avatar_position));
    setNarration(info?.settings?.narration !== false);
    setNarrationScenes(null);
    setVideoAudioMode(info?.settings?.video_audio_mode || "AUTO");
    setClipAudio(initialClipAudio(info));
    setClipAudioTouched(false);
    setMusicVolume(info?.settings?.music_volume ?? 0.07);
    setVisualContinuity(info?.settings?.visual_continuity || "");
    setReviewStartingFrames(!!info?.settings?.review_starting_frames);
    setGenerationMode(info?.settings?.generation_mode || "STANDARD");
    setPlatform(info?.settings?.platform || "GENERAL");
    setVideoFormat(info?.settings?.video_format || "LANDSCAPE");
    setSubtitles(info?.settings?.subtitles === true);
    setCaptionStyle(info?.settings?.caption_style || (info?.settings?.platform === "TIKTOK" ? "TIKTOK" : "CLASSIC"));
    setCaptionConfig(info?.settings?.caption_config || {});
    setTransitionDefault(defaultTransition(info?.settings));
    setTransitionDuration(info?.settings?.transition_duration ?? "");
    setIntroTransition(info?.settings?.intro_transition || "DEFAULT");
    setIntroTransitionDuration(info?.settings?.intro_transition_duration ?? "");
  }, [info?.settings, showModal]);

  const changePlatform = (value) => {
    setPlatform(value);
    if (value === "TIKTOK") {
      setVideoFormat("PORTRAIT");
      setSubtitles(true);
      setCaptionStyle("TIKTOK");
    }
  };

  const saveSettings = async changes => {
    if (saving) return;
    setSaving(true);
    try {
      const { data: response, status } = await updateVideo(info.id, changes);
      if (response) {
        toast.success(status === 202 ? "Settings saved. Narration is regenerating in the background." : "Video settings saved");
        onSaved?.();
        setShowModal(false);
      }
    } finally {
      setSaving(false);
    }
  };

  const onSubmit = async event => {
    event.preventDefault();
    if (busy || (needsNarrationReview && !narrationScenes)) return;
    const changes = {
      visual_continuity: visualContinuity,
      review_starting_frames: reviewStartingFrames,
      generation_mode: generationMode,
      intro,
      outro,
      avatar,
      subtitles,
      caption_style: captionStyle,
      caption_config: captionConfig,
      platform,
      video_format: videoFormat,
      transition_default: transitionDefault,
      transition_duration: transitionDuration === "" ? null : Number(transitionDuration),
      intro_transition: introTransition,
      intro_transition_duration: introTransitionDuration === "" ? null : Number(introTransitionDuration),
    };
    if (info?.video_type !== "MANUAL") changes.narration = narration;
    if (info?.video_type !== "MANUAL") changes.video_audio_mode = videoAudioMode;
    if (clipAudio !== initialClipAudio(info)) changes.video_audio_enabled = clipAudio;
    if (musicVolume !== (info?.settings?.music_volume ?? 0.07)) changes.music_volume = musicVolume;
    if (needsNarrationReview) changes.narration_scenes = narrationScenes;
    if (!avatar && voice && String(voice) !== String(info?.voice_model ?? "")) changes.voice_id = voice;
    if (avatar) changes.avatar_position = normalizeAvatarPosition(avatarPosition);
    await saveSettings(changes);
  };

  if (!showModal) return null;

  return <EditorDialog open={showModal} onClose={() => setShowModal(false)} title="Video settings" description={`Customize ${info?.title || "your video"} before rendering.`} icon={RiSettings3Line} busy={busy} maxWidth="max-w-4xl" footer={<div className="flex justify-end gap-2">
    {info?.can_retry_narration && <button type="button" disabled={busy} onClick={() => saveSettings({ retry_narration: true })} className={editorSecondaryButton}>Retry narration</button>}
    <button type="button" disabled={busy} onClick={() => setShowModal(false)} className={editorSecondaryButton}>Cancel</button>
    <button type="submit" form="video-settings-form" disabled={busy || (needsNarrationReview && !narrationScenes)} className={editorButton}>{saving ? "Saving…" : needsNarrationReview ? "Save and generate speech" : "Save settings"}</button>
  </div>}>
    <form id="video-settings-form" onSubmit={onSubmit}><fieldset disabled={busy} className="min-w-0 space-y-6">
            {(info?.mode === "AI" || info?.video_type === "MANUAL") && <GenerationModeSelect value={generationMode} onChange={setGenerationMode} disabled={saving} />}
            <StartingFrameOption mode={info?.mode} provider={info?.settings?.provider} checked={reviewStartingFrames} required={!!info?.settings?.character_references} onChange={setReviewStartingFrames} disabled={saving} />
            {(info?.mode === "AI" || info?.video_type === "MANUAL") && <VisualContinuity value={visualContinuity} onChange={setVisualContinuity} disabled={saving} />}
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
                <div><AssetDropBox value={intro} setValue={setIntro} setSelectedFile={setSelectedIntroFile} type="intro" items={intros} selectedFile={selectedIntroFile} />
              <MoreAssetOptions options={introsOptions} label="intros" /></div>
                <div><AssetDropBox value={outro} setValue={setOutro} setSelectedFile={setSelectedOutroFile} type="outro" items={outros} selectedFile={selectedOutroFile} />
              <MoreAssetOptions options={outrosOptions} label="outros" /></div>
              </div>
              {intro && <fieldset disabled={saving} className="mt-4 grid gap-4 rounded-xl border border-gray-200 p-4 sm:grid-cols-2 dark:border-gray-700">
                <legend className="px-2 text-sm font-semibold text-gray-700 dark:text-gray-200">After intro</legend>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-200">Transition to first scene
                  <select aria-label="After intro transition" className="mt-2 block w-full rounded-xl border border-gray-200 bg-white p-3 text-sm dark:border-gray-700 dark:bg-gray-800" value={introTransition} onChange={event => setIntroTransition(event.target.value)}>
                    <option value="DEFAULT">Video default</option>
                    {transitionStyles.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                </label>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-200">Duration
                  <select aria-label="After intro transition duration" disabled={saving || (introTransition === "DEFAULT" ? transitionDefault : introTransition) === "CUT"} className="mt-2 block w-full rounded-xl border border-gray-200 bg-white p-3 text-sm disabled:opacity-50 dark:border-gray-700 dark:bg-gray-800" value={introTransitionDuration} onChange={event => setIntroTransitionDuration(event.target.value)}>
                    <option value="">Video default ({transitionDuration ? `${transitionDuration}s` : "Automatic"})</option>
                    {transitionDurations.map(value => <option key={value} value={value}>{value}s</option>)}
                  </select>
                </label>
              </fieldset>}
            </section>

            <section className="rounded-2xl border border-gray-200 bg-gray-50/70 p-4 sm:p-5 dark:border-gray-800 dark:bg-gray-800/40">
              <div className="mb-4 flex items-start gap-3"><span className="mt-0.5 text-indigo-600 dark:text-indigo-300"><RiUser3Line aria-hidden="true" className="h-5 w-5" /></span><div><h3 className={sectionTitle}>{info?.video_type === "MANUAL" ? "Audio and captions" : "Narration, audio and captions"}</h3><p className={sectionDescription}>{info?.video_type === "MANUAL" ? "Show the caption text you add to your scenes." : "Choose a presenter or narration voice, and subtitle visibility."}</p></div></div>
              {info?.video_type !== "MANUAL" && <AssetDropBox value={avatar} setValue={setAvatar} setSelectedFile={setSelectedAvatarFile} type="avatar" items={avatars} selectedFile={selectedAvatarFile} />}
              {info?.video_type !== "MANUAL" && <MoreAssetOptions options={avatarsOptions} label="avatars" />}
              {info?.video_type !== "MANUAL" && <label htmlFor="video-narration" className="mt-5 flex cursor-pointer items-start gap-3 rounded-xl border border-gray-200 bg-white p-3.5 dark:border-gray-700 dark:bg-gray-800">
                <input id="video-narration" type="checkbox" checked={narration} onChange={(event) => { setNarration(event.target.checked); if (!clipAudioTouched && info?.settings?.video_audio_enabled === undefined) setClipAudio(!event.target.checked); }} className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                <span><span className="block text-sm font-semibold text-gray-800 dark:text-gray-100">Narration</span><span className="mt-1 block text-xs text-gray-500 dark:text-gray-400">Read your scene text aloud using the selected voice. Enabling narration generates speech in the background. Turning it off keeps saved recordings.</span></span>
              </label>}
              {showModal && needsNarrationReview && <NarrationSetup video={info} disabled={saving} onChange={setNarrationScenes} onBusyChange={setWritingNarration} />}
              <fieldset className="mt-5 space-y-4 rounded-xl border border-gray-200 p-4 dark:border-gray-700">
                <legend className="px-1 text-sm font-semibold">What the audience hears</legend>
                <label className="flex items-start gap-3 text-sm"><input type="checkbox" checked={clipAudio} onChange={event => { setClipAudio(event.target.checked); setClipAudioTouched(true); }} className="mt-1" /><span>Include original clip audio<span className="mt-1 block text-xs text-gray-500 dark:text-gray-400">Include dialogue, ambient sound and effects recorded in the scene clips. Only clips with audio enabled under Visual will play.</span></span></label>
                {info?.video_type !== "MANUAL" && <label className="block text-sm font-medium">Sound for newly generated clips<select aria-label="Generated clip sound" value={videoAudioMode} onChange={event => setVideoAudioMode(event.target.value)} className={`${editorInput} mt-2`}>
                  <option value="AUTO">Automatic — {narration ? "ambient sound, no character speech" : "character dialogue allowed"}</option>
                  <option value="DIALOGUE">Character dialogue and ambient sound</option>
                  <option value="AMBIENT">Ambient sound only</option>
                  <option value="SILENT">Silent</option>
                </select><span className="mt-2 block text-xs font-normal text-gray-500 dark:text-gray-400">Applies when generating or regenerating a clip. Audio support depends on the provider. Existing recordings stay as they are.</span></label>}
                {!clipAudio && videoAudioMode !== "SILENT" && <p className="text-xs text-gray-500 dark:text-gray-400">Original clip audio is muted in the final edit. Enable it above to hear generated dialogue and ambient sound.</p>}
                {narration && clipAudio && (videoAudioMode === "DIALOGUE") && <p className="text-xs text-amber-700 dark:text-amber-300">Narration and character dialogue will both be heard. Keep spoken lines separate to avoid overlapping speech.</p>}
                <label className="block text-sm font-medium">Background music volume — {Math.round(musicVolume * 100)}%<input aria-label="Background music volume" type="range" min="0" max="100" step="1" value={Math.round(musicVolume * 100)} onChange={event => setMusicVolume(Number(event.target.value) / 100)} className="mt-3 block w-full accent-blue-600" /><span className="mt-1 block text-xs font-normal text-gray-500 dark:text-gray-400">{info?.music ? "Set to 0% to mute the soundtrack. More music controls are in Project extras." : "Add a soundtrack in Project extras to hear background music."}</span></label>
              </fieldset>
              {!avatar && info?.video_type !== "MANUAL" && (
                <div className="mt-5">
                  <label htmlFor="video-voice" className="mb-2 block text-sm font-semibold text-gray-800 dark:text-gray-100">Narration voice</label>
                  <select id="video-voice" value={voice} onChange={(event) => setVoice(event.target.value)} disabled={saving || !narration} required={narration} className="w-full rounded-xl border border-gray-200 bg-white px-3.5 py-3 text-sm text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50 dark:border-gray-700 dark:bg-gray-800 dark:text-white">
                    <option value="" disabled>{voicesOptions.loading ? "Loading voices…" : "Choose a voice"}</option>
                    {voice && !voices.some((item) => String(item.id) === String(voice)) && <option value={voice}>Current voice</option>}
                    {voices.map((item) => <option key={item.id} value={item.id}>{item.name} ({item.provider})</option>)}
                  </select>
                  <MoreAssetOptions options={voicesOptions} label="voices" />
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{!narration ? "Enable narration to choose a voice." : "Changing the voice regenerates narration for your scenes."}</p>
                </div>
              )}
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
                <span className="flex-1"><span className="block text-sm font-semibold text-gray-800 dark:text-gray-100">Subtitles</span><span className="mt-0.5 block text-xs text-gray-500 dark:text-gray-400">{info?.video_type === "MANUAL" ? "Show the text you add to each scene." : "Show narration as on-screen captions."}</span></span>
                <span className={`relative h-6 w-11 rounded-full transition ${subtitles ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"}`} aria-hidden="true"><span className={`absolute top-1 h-4 w-4 rounded-full bg-white shadow transition-all ${subtitles ? "left-6" : "left-1"}`} /></span>
              </label>
              {subtitles && <div className="mt-3"><CaptionStyleEditor preset={captionStyle} config={captionConfig} videoFormat={videoFormat} onChange={(preset, config) => { setCaptionStyle(preset); setCaptionConfig(config); }} /></div>}
            </section>
    </fieldset></form>
  </EditorDialog>;
};
