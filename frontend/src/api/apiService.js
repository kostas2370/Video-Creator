import { toast } from "react-toastify";
import { axiosPrivateInstance } from "./axiosPrivate";

const firstErrorMessage = (error) => {
    const data = error?.response?.data;
    if (!data) return "The server could not be reached";
    if (typeof data === "string") return data;

    const [field, detail] = Object.entries(data)[0] ?? [];
    if (!field) return "The request was refused";
    return Array.isArray(detail) ? `${field}: ${detail[0]}` : `${field}: ${detail}`;
};

const reportFailure = (error, action) => {
    const message = firstErrorMessage(error);
    console.error(`${action}:`, error);
    toast.error(message, { toastId: `${action}:${message}` });
};

const API_ENDPOINTS = {
    INTRO: 'intros/',
    OUTRO: 'outros/',
    GENERATE: 'generate/',
    TWITCH_GENERATE: 'twitch_generate/',
    AVATAR: 'avatars/',
    LOGOUT: 'logout/',
    VOICES: 'voices/',
    SCENE: (id) => `videos/${id}/add_scene/`,
    AVATAR_SELECT: (id) => `avatars/${id}/`,
    VIDEO_SELECT: (id) => `videos/${id}/`,
    INTRO_SELECT: (id) => `intros/${id}/`,
    OUTRO_SELECT: (id) => `outros/${id}/`,
    SCENE_SELECT: (id) => `scenes/${id}/`,
    SCENE_IMAGE_SELECT: (id) => `scene_images/${id}/`,
    RENDER: (id) => `videos/${id}/render_video/`,
    RESUME: (id) => `videos/${id}/resume/`,
    SCENE_GENERATE : (id) => `scenes/${id}/generate/`,
    SCENE_IMAGE_GENERATE : (id) => `scenes/${id}/generate_image_scene/`,
    TEMPLATES : 'templates/' ,
    TEMPLATE_SELECT: (id) => `templates/${id}/`,
    INTRO_GET: (search = null) => `intros/${search ? `?search=${search}` : ''}`,
    OUTRO_GET: (search = null) => `outros/${search ? `?search=${search}` : ''}`,
    VIDEOS_GET: (search = null, page = null, id = null) => {
        let url = 'videos/';
        if (id){
            return url+id+"/"
        }

        const params = [];
        if (search) params.push(`search=${encodeURIComponent(search)}`);
        if (page) params.push(`page=${encodeURIComponent(page)}`);
        return params.length > 0 ? `${url}?${params.join('&')}` : url;
    },
    GET_AVATARS: (name = null) => `avatars/${name ? `?search=${name}` : ''}`,
    API_KEYS: 'api_keys/',
    NOTIFICATIONS: 'notifications/',
    NOTIFICATION_SELECT: (id) => `notifications/${id}/`,
    NOTIFICATIONS_READ_ALL: 'notifications/read_all/',


};


const getRequest = async (url, params = {}, axiosInstance = axiosPrivateInstance) => {
    try {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;

        const response = await axiosInstance.get(fullUrl);
        return response.data;
    } catch (error) {
        reportFailure(error, `Could not load ${url}`);
    }
}


const postRequest = async (url, data) => {
    try {
        const response = await axiosPrivateInstance.post(url, data);
        return response.data;
    } catch (error) {
        reportFailure(error, `Could not save to ${url}`);
    }
};

const deleteRequest = async (url, axiosInstance = axiosPrivateInstance) => {
    try {
        const response = await axiosInstance.delete(url);
        return response.data;
    } catch (error) {
        reportFailure(error, `Could not delete ${url}`);
    }
}

const JSON_CONFIG = { headers: { "Content-Type": "application/json" } };

const patchRequest = async (url,data, axiosInstance = axiosPrivateInstance, config = {}) => {
    try {
        const response = await axiosInstance.patch(url,data, config);
        return response.data;
    } catch (error) {
        reportFailure(error, `Could not update ${url}`);
    }
}

export const createScene = async (id, data) => {return postRequest(API_ENDPOINTS.SCENE(id), data);}
export const createIntro = async (data) => {return postRequest(API_ENDPOINTS.INTRO, data)}
export const createOutro = async (data) => {return postRequest(API_ENDPOINTS.OUTRO, data)}
export const createAvatar = async (data) => {return postRequest(API_ENDPOINTS.AVATAR,data)}
export const generateVideo = async (data) => {return postRequest(API_ENDPOINTS.GENERATE, data)}
export const generateTwitchVideo = async (data) => {return postRequest(API_ENDPOINTS.TWITCH_GENERATE, data)}
export const deleteAvatar = async (id) => {return deleteRequest(API_ENDPOINTS.AVATAR_SELECT(id))}
export const deleteVideo = async (id) =>  {return deleteRequest(API_ENDPOINTS.VIDEO_SELECT(id))}
export const deleteIntro = async (id) => {return deleteRequest(API_ENDPOINTS.INTRO_SELECT(id))}
export const deleteOutro = async (id) => {return deleteRequest(API_ENDPOINTS.OUTRO_SELECT(id))}
export const deleteImageScene = async (id) =>  {return deleteRequest(API_ENDPOINTS.SCENE_IMAGE_SELECT(id))}
export const deleteScene = async (id) =>  {return deleteRequest(API_ENDPOINTS.SCENE_SELECT(id))}
export const deleteTemplate = async (id) => {return deleteRequest(API_ENDPOINTS.TEMPLATE_SELECT(id))}

export const updateScene = async (id, data) => {return patchRequest(API_ENDPOINTS.SCENE_SELECT(id),data)}
export const updateVideo = async (id,data) => {return patchRequest(API_ENDPOINTS.VIDEO_SELECT(id), data, axiosPrivateInstance, JSON_CONFIG)}
export const resumeVideo = async (id) => {
    try {
        const response = await axiosPrivateInstance.patch(API_ENDPOINTS.RESUME(id), {});
        return { ok: true, data: response.data };
    } catch (error) {
        console.error(`Error resuming the generation of video ${id}:`, error);
        return {
            ok: false,
            status: error?.response?.status,
            message: error?.response?.data?.message || "The generation could not be resumed",
        };
    }
}

export const renderVideo = async (id) => {
    try {
        const response = await axiosPrivateInstance.patch(API_ENDPOINTS.RENDER(id), {});
        return { ok: true, data: response.data };
    } catch (error) {
        console.error(`Error queueing the render of video ${id}:`, error);
        return {
            ok: false,
            status: error?.response?.status,
            message: error?.response?.data?.message || "The render could not be queued",
        };
    }
}

const apiKeysRequest = async (method, data = undefined) => {
    try {
        const response = await axiosPrivateInstance.request({
            url: API_ENDPOINTS.API_KEYS,
            method,
            data,
            headers: { "Content-Type": "application/json" },
        });
        return { ok: true, data: response.data };
    } catch (error) {
        console.error(`Error on ${method} ${API_ENDPOINTS.API_KEYS}:`, error);
        return { ok: false, message: firstErrorMessage(error) };
    }
};

export const getApiKeys = async () => {return apiKeysRequest("get")}
export const updateApiKeys = async (data) => {return apiKeysRequest("patch", data)}
export const deleteApiKeys = async () => {return apiKeysRequest("delete")}

export const generateScene = async (id, data) => {return patchRequest(API_ENDPOINTS.SCENE_GENERATE(id),data)}
export const generateSceneImage = async (id, data) => {return postRequest(API_ENDPOINTS.SCENE_IMAGE_GENERATE(id), data)}
export const logout = async () => {return postRequest(API_ENDPOINTS.LOGOUT)}
export const getVoices = async () => {return getRequest(API_ENDPOINTS.VOICES);}
export const getTemplates = async () => {return getRequest(API_ENDPOINTS.TEMPLATES)}
export const getNotifications = async () => {return getRequest(API_ENDPOINTS.NOTIFICATIONS)}
export const markNotificationRead = async (id) => {return patchRequest(API_ENDPOINTS.NOTIFICATION_SELECT(id), { read: true }, axiosPrivateInstance, JSON_CONFIG)}
export const markAllNotificationsRead = async () => {return patchRequest(API_ENDPOINTS.NOTIFICATIONS_READ_ALL, {}, axiosPrivateInstance, JSON_CONFIG)}
export const createTemplate = async (data) => {
    try {
        const response = await axiosPrivateInstance.post(API_ENDPOINTS.TEMPLATES, data);
        return { ok: true, template: response.data };
    } catch (error) {
        console.error("Error saving the template:", error);
        const detail = error?.response?.data;
        const firstField = detail && Object.values(detail)[0];
        return {
            ok: false,
            status: error?.response?.status,
            message: (Array.isArray(firstField) ? firstField[0] : firstField)
                || "The template could not be saved",
        };
    }
}
export const getIntro = async (search = null) => {return getRequest(API_ENDPOINTS.INTRO_GET(search));}
export const getOutro = async (search = null) => {return getRequest(API_ENDPOINTS.OUTRO_GET(search));}
export const getVideos = async (search = null, page = null) => {return getRequest(API_ENDPOINTS.VIDEOS_GET(search, page));}
export const getAvatars = async (name = null) => {return getRequest(API_ENDPOINTS.GET_AVATARS(name));}
export const getVideo = async (id) => {return getRequest(API_ENDPOINTS.VIDEO_SELECT(id))};
export const updateSceneImage = async (id,scene_image_id, data) => {

    try{
        var url = "scenes/" + id +"/change_image_scene/"
        if (scene_image_id){
            url = url + "?scene_image=" + scene_image_id;

        }
        const response = await axiosPrivateInstance.post(url, data);

        return response.data

    }catch (error){
        reportFailure(error, "Could not change the scene image");
    }
}