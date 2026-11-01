import { request } from "./request";
import { waitForSceneOperation } from "./sceneOperation";
import { toast } from "react-toastify";
import { axiosInstance } from "./axiosPrivate";
import { LOGIN_URL, REGISTER_URL, REFRESH_URL, PASSWORD_RESET_URL, PASSWORD_RESET_CONFIRM_URL, PASSWORD_RESET_VALIDATE_URL } from "../endpoints";

const detail = (resource, id) => `${resource}/${encodeURIComponent(id)}/`;
const action = (resource, id, name) => `${detail(resource, id)}${name}/`;
const get = (url, params) => request({ url, params });
const post = (url, data, options = {}) => request({ method: "post", url, data, ...options });
const patch = (url, data, options = {}) => request({ method: "patch", url, data, ...options });
const remove = (url, options = {}) => request({ method: "delete", url, ...options });
const callerHandlesErrors = { notifyError: false };
const publicRequest = (url, data) => post(url, data, { client: axiosInstance, ...callerHandlesErrors });

export const getNewsUpdates = (page = 1) => request({
  url: "news/", params: { page }, client: axiosInstance, ...callerHandlesErrors,
});

export const login = data => publicRequest(LOGIN_URL, data);
export const register = data => publicRequest(REGISTER_URL, data);
export const refreshToken = () => publicRequest(REFRESH_URL);
export const requestPasswordReset = data => publicRequest(PASSWORD_RESET_URL, data);
export const validatePasswordReset = data => publicRequest(PASSWORD_RESET_VALIDATE_URL, data);
export const confirmPasswordReset = data => publicRequest(PASSWORD_RESET_CONFIRM_URL, data);
export const logout = () => post("logout/", undefined, callerHandlesErrors);

export const getIntro = (search, page = 1) => get("intros/", { search: search || undefined, page });
export const getOutro = (search, page = 1) => get("outros/", { search: search || undefined, page });
export const getAvatars = (search, page = 1) => get("avatars/", { search: search || undefined, page });
export const getVideos = (search, page, status, filters = {}) => get("videos/", { search: search || undefined, page: page || undefined, status: status || undefined, ...filters });
export const toggleVideoFavorite = id => patch(action("videos", id, "favorite"));
export const ensureVideoThumbnail = id => post(action("videos", id, "thumbnail"), {}, callerHandlesErrors);
export const getVideoSubtitles = id => request({ url: action("videos", id, "subtitles"), ...callerHandlesErrors });
export const getVideoPreview = id => request({ url: action("videos", id, "preview"), ...callerHandlesErrors });
export const getVideo = (id, options = {}) => request({ url: detail("videos", id), ...options });
export const getVoices = (search, page = 1, { is_cloned, notifyError = true } = {}) => request({
  url: "voices/", params: { search: search || undefined, page, is_cloned }, notifyError,
});
export const cloneVoice = data => post("voices/clone/", data, callerHandlesErrors);
export const previewVoice = id => post(action("voices", id, "preview"), {}, { ...callerHandlesErrors, responseType: "blob" });
export const refreshVoice = id => post(action("voices", id, "refresh"), {}, callerHandlesErrors);
export const deleteVoice = id => remove(detail("voices", id), callerHandlesErrors);
export const getTemplates = (search, page = 1) => get("templates/", { search: search || undefined, page });
export const getNotifications = (options = {}) => request({ url: "notifications/", ...options });
export const getUsage = period => request({ url: "usage/", params: { period }, notifyError: false });

export const createIntro = data => post("intros/", data);
export const createOutro = data => post("outros/", data);
export const createAvatar = data => post("avatars/", data);
export const createStoryVideo = data => post("videos/story/", data, callerHandlesErrors);
export const draftStory = data => post("videos/draft_story/", data, callerHandlesErrors);
export const getCaptionProjects = params => request({ url: "captions/", params, ...callerHandlesErrors });
export const getCaptionProject = id => request({ url: detail("captions", id), ...callerHandlesErrors });
export const createCaptionProject = data => post("captions/", data, callerHandlesErrors);
export const saveCaptionProject = (id, data) => patch(`captions/${id}/`, data, callerHandlesErrors);
export const transcribeCaptionProject = id => post(`captions/${id}/transcribe/`, {}, callerHandlesErrors);
export const renderCaptionProject = id => post(`captions/${id}/render/`, {}, callerHandlesErrors);
export const downloadCaptionProject = (id, subtitles = false) => request({ url: action("captions", id, subtitles ? "subtitles" : "download"), responseType: "blob", ...callerHandlesErrors });
export const createManualVideo = data => post("videos/manual/", data, callerHandlesErrors);
export const uploadMusic = (id, data) => post(action("videos", id, "music"), data, callerHandlesErrors);
export const removeMusic = id => remove(action("videos", id, "music"), callerHandlesErrors);
export const generateVideo = data => post("generate/", data);
export const approveScript = (id, data) => post(action("videos", id, "approve_script"), data, callerHandlesErrors);
export const reorderScenes = (id, sceneIds, expectedSceneIds) => post(action("videos", id, "reorder_scenes"), { scene_ids: sceneIds, ...(expectedSceneIds ? { expected_scene_ids: expectedSceneIds } : {}) }, callerHandlesErrors);
export const getDeletedScenes = (id, page = 1) => request({ url: action("videos", id, "deleted_scenes"), params: { page }, ...callerHandlesErrors });
export const archiveScene = (id, sceneIds) => post(action("scenes", id, "archive"), { scene_ids: sceneIds }, callerHandlesErrors);
export const restoreScene = (id, sceneIds, expectedSceneIds) => post(action("scenes", id, "restore"), { ...(sceneIds ? { scene_ids: sceneIds } : {}), expected_scene_ids: expectedSceneIds }, callerHandlesErrors);
export const createScene = (id, data) => post(action("videos", id, "add_scene"), data);
export const draftScene = (id, data) => post(action("videos", id, "draft_scene"), data, callerHandlesErrors);
export const createTemplate = data => post("templates/", data, callerHandlesErrors);

const sceneOperation = async (id, send) => {
  const queued = await send();
  if (!queued.ok || queued.status !== 202) return queued;
  const result = await waitForSceneOperation(() => request({ url: action("scenes", id, "operation"), params: { job: queued.data.id }, notifyError: false }));
  if (!result.ok) toast.error(result.message || "Could not finish the scene operation.");
  return result;
};

export const getSceneWaveform = id => request({ url: action("scenes", id, "waveform"), ...callerHandlesErrors });
export const updateSceneAudio = (id, data) => patch(action("scenes", id, "audio"), data, callerHandlesErrors);
export const uploadVoiceover = (id, data) => post(action("scenes", id, "voiceover"), data, callerHandlesErrors);
export const removeVoiceover = id => remove(action("scenes", id, "voiceover"), callerHandlesErrors);
export const updateMusicAudio = (id, data) => patch(action("videos", id, "audio"), data, callerHandlesErrors);


export const applyAutoMotion = (id, intensity) => patch(action("videos", id, "auto_motion"), { motion_intensity: intensity }, callerHandlesErrors);
export const updateSceneMotion = (id, changes) => patch(action("scenes", id, "motion"), changes, callerHandlesErrors);
export const updateSceneTiming = (id, changes) => patch(action("scenes", id, "timing"), changes, callerHandlesErrors);
export const updateSceneTransition = (id, changes) => patch(action("scenes", id, "transition"), changes, callerHandlesErrors);
export const updateScene = (id, data) => sceneOperation(id, () => patch(detail("scenes", id), data));
export const generateVideoTags = (id, previousTags) => post(action("videos", id, "generate_tags"), { previous_tags: previousTags }, callerHandlesErrors);
export const saveVideoTags = (id, tags, previousTags) => patch(action("videos", id, "tags"), { tags, previous_tags: previousTags }, callerHandlesErrors);
export const saveVideoNotes = (id, notes, previousNotes) => patch(`${detail("videos", id)}notes/`, { notes, previous_notes: previousNotes }, callerHandlesErrors);
export const updateVideo = (id, data) => patch(detail("videos", id), data);
export const generateScene = (id, data) => sceneOperation(id, () => patch(action("scenes", id, "generate"), data));
export const updateStartingImage = (id, data) => sceneOperation(id, () => post(action("scenes", id, "starting_image"), data, callerHandlesErrors));
export const generateSceneImage = (id, data) => sceneOperation(id, () => post(action("scenes", id, "generate_image_scene"), data));
export const updateSceneImage = (id, imageId, data) => request({ method: "post", url: action("scenes", id, "change_image_scene"), data, params: { scene_image: imageId || undefined } });
export const resumeVideo = id => patch(action("videos", id, "resume"), {}, callerHandlesErrors);
export const renderVideo = (id, options = {}) => patch(action("videos", id, "render_video"), options, callerHandlesErrors);

export const deleteIntro = id => remove(detail("intros", id));
export const deleteOutro = id => remove(detail("outros", id));
export const deleteAvatar = id => remove(detail("avatars", id));
export const deleteVideo = id => remove(detail("videos", id));
export const deleteScene = id => remove(detail("scenes", id));
export const deleteImageScene = id => remove(detail("scene_images", id));
export const deleteTemplate = id => remove(detail("templates", id));

export const getApiKeys = () => request({ url: "api_keys/", ...callerHandlesErrors });
export const updateApiKeys = data => patch("api_keys/", data, callerHandlesErrors);
export const deleteApiKeys = () => remove("api_keys/", callerHandlesErrors);
export const getCustomTtsProviders = () => request({ url: "user-custom-tts-providers/", ...callerHandlesErrors });
export const createCustomTtsProvider = data => post("user-custom-tts-providers/", data, callerHandlesErrors);
export const updateCustomTtsProvider = (id, data) => patch(detail("user-custom-tts-providers", id), data, callerHandlesErrors);
export const deleteCustomTtsProvider = id => remove(detail("user-custom-tts-providers", id), callerHandlesErrors);
export const refreshCustomTtsProviderVoices = id => post(action("user-custom-tts-providers", id, "update-voices"), {}, callerHandlesErrors);
export const getCustomVisualProviders = () => request({ url: "user-custom-visual-providers/", ...callerHandlesErrors });
export const createCustomVisualProvider = data => post("user-custom-visual-providers/", data, callerHandlesErrors);
export const updateCustomVisualProvider = (id, data) => patch(detail("user-custom-visual-providers", id), data, callerHandlesErrors);
export const deleteCustomVisualProvider = id => remove(detail("user-custom-visual-providers", id), callerHandlesErrors);
export const markNotificationRead = id => patch(detail("notifications", id), { read: true });
export const markAllNotificationsRead = () => patch("notifications/read_all/", {});

export const updateSceneOverlays = (id, data) => patch(action("scenes", id, "overlays"), data, callerHandlesErrors);
export const getSceneCaptions = id => request({ url: action("scenes", id, "captions"), ...callerHandlesErrors });
export const updateSceneCaptions = (id, data) => patch(action("scenes", id, "captions"), data, callerHandlesErrors);

export const getCaptionStyles = () => request({ url: "videos/caption_styles/", ...callerHandlesErrors });

export const getMediaAssets = (search, page = 1, kind) => get("media-assets/", { search: search || undefined, page: page || 1, kind: kind || undefined });
export const createMediaAsset = data => post("media-assets/", data, callerHandlesErrors);
export const editMediaAsset = (id, data) => patch(detail("media-assets", id), data, callerHandlesErrors);
export const downloadMediaAsset = id => request({ url: action("media-assets", id, "download"), responseType: "blob", ...callerHandlesErrors });
export const deleteMediaAsset = id => remove(detail("media-assets", id), callerHandlesErrors);
export const useMediaAsset = (id, data) => post(action("media-assets", id, "use"), data, callerHandlesErrors);
export const previewVideoCover = (id, data) => post(action("videos", id, "cover_preview"), data, { ...callerHandlesErrors, responseType: "blob" });
export const generateVideoCover = (id, data) => post(action("videos", id, "cover_generate"), data, callerHandlesErrors);
export const getVideoCoverJob = (id, job, image = false) => request({ url: action("videos", id, "cover_job"), params: { job, ...(image ? { image: "1" } : {}) }, ...(image ? { responseType: "blob" } : {}), ...callerHandlesErrors });
export const saveVideoCover = (id, data) => post(action("videos", id, "cover"), data, callerHandlesErrors);
export const downloadVideoCover = id => request({ url: action("videos", id, "cover_download"), responseType: "blob", ...callerHandlesErrors });

export const getSocialConnections = () => request({ url: "publishing/connections/", ...callerHandlesErrors });
export const disconnectSocialAccount = id => remove(`publishing/connections/${id}/`, callerHandlesErrors);
export const connectSocialAccount = (platform, video) => post(`publishing/oauth/${platform}/start/`, { video }, callerHandlesErrors);
export const getPostingContext = id => request({ url: `publishing/connections/${id}/context/`, ...callerHandlesErrors });
export const getPublishJobs = video => request({ url: "publishing/jobs/", params: { video }, ...callerHandlesErrors });
export const publishVideo = data => post("publishing/jobs/", data, callerHandlesErrors);
export const refreshPublishStatus = id => post(`publishing/jobs/${id}/refresh/`, {}, callerHandlesErrors);

export const draftYouTubeDescription = (id, mode) => post(action("videos", id, "youtube_description"), { mode }, callerHandlesErrors);

export const saveVideoDetails = (id, details, previousDetails) => patch(action("videos", id, "details"), { ...details, previous_details: previousDetails }, callerHandlesErrors);
export const draftVideoTags = id => post(action("videos", id, "draft_tags"), {}, callerHandlesErrors);

export const getSeries = (search, page = 1) => request({ url: "series/", params: { search: search || undefined, page }, ...callerHandlesErrors });
export const getSeriesProfile = id => request({ url: detail("series", id), ...callerHandlesErrors });
export const createSeries = data => post("series/", data, callerHandlesErrors);
export const draftSeriesCast = data => post("series/cast_draft/", data, callerHandlesErrors);
export const draftCharacterDescription = data => post("series/character_description/", data, callerHandlesErrors);
export const createCharacterReference = data => post("series/character_references/", data, callerHandlesErrors);
export const getCharacterReference = id => request({ url: "series/character_references/", params: { id }, ...callerHandlesErrors });
export const updateSeries = (id, data) => patch(detail("series", id), data, callerHandlesErrors);
export const deleteSeries = id => remove(detail("series", id), callerHandlesErrors);
export const getSeriesEpisodes = (id, page = 1) => request({ url: action("series", id, "episodes"), params: { page }, ...callerHandlesErrors });
export const draftSeriesEpisode = (id, idea) => post(action("series", id, "episodes"), { idea }, callerHandlesErrors);
export const saveEpisodeMemory = (seriesId, episodeId, summary, previousSummary, scriptHash) => patch(`${action("series", seriesId, "episodes")}${encodeURIComponent(episodeId)}/`, { summary, script_hash: scriptHash, previous_summary: previousSummary }, callerHandlesErrors);
export const retrySeriesEpisode = (seriesId, episodeId) => post(`${action("series", seriesId, "episodes")}${encodeURIComponent(episodeId)}/retry/`, {}, callerHandlesErrors);

export const draftEpisodeMemory = (seriesId, episodeId, summary) => post(`${action("series", seriesId, "episodes")}${encodeURIComponent(episodeId)}/draft_memory/`, { summary }, callerHandlesErrors);

export const getClipProjects = (page = 1, filters = {}) => request({ url: "clips/", params: { page, ...filters }, ...callerHandlesErrors });
export const getClipProject = id => request({ url: detail("clips", id), ...callerHandlesErrors });
export const createClipProject = data => post("clips/", data, callerHandlesErrors);
export const retryClipProject = id => post(action("clips", id, "retry"), {}, callerHandlesErrors);
export const deleteClipProject = id => remove(detail("clips", id), callerHandlesErrors);
export const createClip = (id, data) => post(action("clips", id, "clips"), data, callerHandlesErrors);
export const saveClip = (id, clipId, data) => patch(`${action("clips", id, "clips")}${encodeURIComponent(clipId)}/`, data, callerHandlesErrors);
export const deleteClip = (id, clipId) => remove(`${action("clips", id, "clips")}${encodeURIComponent(clipId)}/`, callerHandlesErrors);
export const exportClips = (id, clipIds) => post(action("clips", id, "export"), { clip_ids: clipIds }, callerHandlesErrors);
export const downloadClip = (id, clipId) => request({ url: `${action("clips", id, "clips")}${encodeURIComponent(clipId)}/download/`, responseType: "blob", ...callerHandlesErrors });

export const draftClipHashtags = (id, clipId) => post(`${action("clips", id, "clips")}${encodeURIComponent(clipId)}/hashtags/`, {}, callerHandlesErrors);
export const saveClipHashtags = (id, clipId, hashtags, previousHashtags) => patch(`${action("clips", id, "clips")}${encodeURIComponent(clipId)}/hashtags/`, { hashtags, previous_hashtags: previousHashtags }, callerHandlesErrors);
export const getClipProjectProgress = id => request({ url: action("clips", id, "progress"), ...callerHandlesErrors });
export const getClip = (id, clipId) => request({ url: `${action("clips", id, "clips")}${encodeURIComponent(clipId)}/`, ...callerHandlesErrors });

export const searchClipTranscript = (id, prompt) => post(action("clips", id, "search-transcript"), { prompt }, callerHandlesErrors);
