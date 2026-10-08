import { request } from "./request";
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

export const login = data => publicRequest(LOGIN_URL, data);
export const register = data => publicRequest(REGISTER_URL, data);
export const refreshToken = () => publicRequest(REFRESH_URL);
export const requestPasswordReset = data => publicRequest(PASSWORD_RESET_URL, data);
export const validatePasswordReset = data => publicRequest(PASSWORD_RESET_VALIDATE_URL, data);
export const confirmPasswordReset = data => publicRequest(PASSWORD_RESET_CONFIRM_URL, data);
export const logout = () => post("logout/", undefined, callerHandlesErrors);

export const getIntro = search => get("intros/", { search: search || undefined });
export const getOutro = search => get("outros/", { search: search || undefined });
export const getAvatars = search => get("avatars/", { search: search || undefined });
export const getVideos = (search, page) => get("videos/", { search: search || undefined, page: page || undefined });
export const getVideo = (id, options = {}) => request({ url: detail("videos", id), ...options });
export const getVoices = () => get("voices/");
export const getTemplates = () => get("templates/");
export const getNotifications = (options = {}) => request({ url: "notifications/", ...options });

export const createIntro = data => post("intros/", data);
export const createOutro = data => post("outros/", data);
export const createAvatar = data => post("avatars/", data);
export const generateVideo = data => post("generate/", data);
export const createScene = (id, data) => post(action("videos", id, "add_scene"), data);
export const draftScene = (id, data) => post(action("videos", id, "draft_scene"), data, callerHandlesErrors);
export const createTemplate = data => post("templates/", data, callerHandlesErrors);

export const updateScene = (id, data) => patch(detail("scenes", id), data);
export const updateVideo = (id, data) => patch(detail("videos", id), data);
export const generateScene = (id, data) => patch(action("scenes", id, "generate"), data);
export const generateSceneImage = (id, data) => post(action("scenes", id, "generate_image_scene"), data);
export const updateSceneImage = (id, imageId, data) => request({ method: "post", url: action("scenes", id, "change_image_scene"), data, params: { scene_image: imageId || undefined } });
export const resumeVideo = id => patch(action("videos", id, "resume"), {}, callerHandlesErrors);
export const renderVideo = id => patch(action("videos", id, "render_video"), {}, callerHandlesErrors);

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
