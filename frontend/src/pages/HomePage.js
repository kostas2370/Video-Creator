import React, { useState, useEffect, useRef } from "react";
import { getAvatars, getTemplates, getVoices } from "../api/apiService";
import { toast } from "react-toastify";
import { generateVideo } from "../api/apiService";
import { pollVideo } from "../api/pollVideo";
import { LoadingButton } from "../components/ui/LoadingButton";
import { ProceedModal } from "../components/ProceedModal";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";

const inputClassName =
  "w-full p-2.5 mt-2 bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-600 focus:border-primary-600 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500";

const Home = () => {
  const isOpenFunction = (data) => {
    setOpen(data);
  };
  const [avatars, setAvatars] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [voices, setVoices] = useState([]);
  const [settings, setSettings] = useState(false);
  const [open, setOpen] = useState(false);
  const [video_id, setVideo_id] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const [formData, setFormData] = useState({
    genre: "",
    template: "",
    avatar_selection: "",
    voice_id: "",
    message: "",
    target_audience: "",
    image_mode: "WEB",
    gpt_model: "gpt-5.4-mini",
    style: "natural",
    music: "",
    provider: "",
    subtitles: true,
    narration: true,
    avatar_position: "top,left",
  });

  const axiosPrivateInstance = useAxiosPrivate();
  const pollRef = useRef(null);

  useEffect(() => () => pollRef.current?.cancel(), []);

  const handleInputChange = (event) => {
    const { name, value, type, checked } = event.target;

    if (type === "checkbox") {
      setFormData((prevData) => ({ ...prevData, [name]: checked }));
      return;
    }

    if (name === "template") {
      const selectedTemplate = templates.find(
        (t) => String(t.id) === String(value)
      );

      if (selectedTemplate) {
        setFormData((prevData) => ({
          ...prevData,
          template: selectedTemplate.id,
          message: selectedTemplate.message ?? prevData.message,
          genre: selectedTemplate.genre ?? "",
          target_audience: selectedTemplate.target_audience ?? "",
          avatar_selection: selectedTemplate.avatar_selection ?? "",
          voice_id: selectedTemplate.voice_id ?? "",
          gpt_model: selectedTemplate.gpt_model ?? prevData.gpt_model,
          image_mode: selectedTemplate.image_mode ?? prevData.image_mode,
          style: selectedTemplate.style ?? prevData.style,
          music: selectedTemplate.music ?? "",
          provider:
            selectedTemplate.provider ??
            (selectedTemplate.image_mode === "AI" ? "DALL-E" : "bing"),
          subtitles: selectedTemplate.subtitles ?? prevData.subtitles,
          narration: selectedTemplate.narration ?? prevData.narration,
          avatar_position:
            selectedTemplate.avatar_position ?? prevData.avatar_position,
        }));
      } else {
        setFormData((prevData) => ({ ...prevData, template: "" }));
      }
      return;
    }

    if (name === "image_mode") {
      setFormData((prevData) => ({
        ...prevData,
        [name]: value,
        provider: value === "AI" ? "DALL-E" : "bing",
      }));
    } else if (name === "avatar_selection") {
      setFormData((prevData) => ({
        ...prevData,
        [name]: value,
        voice_id: value ? "" : prevData.voice_id,
      }));
    } else {
      setFormData((prevData) => ({ ...prevData, [name]: value }));
    }
  };

  useEffect(() => {
    const fetchOptions = async () => {
      axiosPrivateInstance.get("avatars/").then((response) => {
        setAvatars(response.data);
      });

      getVoices().then((response) => {
        setVoices(Array.isArray(response) ? response : []);
      });
      getTemplates().then((response) => {
        setTemplates(Array.isArray(response) ? response : []);
      });
    };

    fetchOptions();
  }, []);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (formData.message.trim() === "") {
      toast.error("You need to add a prompt!");
      return;
    }
    setIsLoading(true);

    const response = await generateVideo(formData);

    if (!response?.video?.id) {
      toast.error("Could not start the generation, please try again.");
      setIsLoading(false);
      return;
    }

    toast.info("Generation started, this usually takes a few minutes...");

    pollRef.current = pollVideo(response.video.id);
    const { outcome, video } = await pollRef.current.promise;

    setIsLoading(false);

    if (outcome !== "SETTLED") {
      toast.error(
        "Lost track of the generation. Check your videos page in a few minutes."
      );
      return;
    }

    if (video.status === "FAILED") {
      toast.error("The generation failed, please try again.");
      return;
    }

    setVideo_id(video.id);
    setOpen(true);
    toast.success("Video generated successfully!");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <ProceedModal open={open} setOpen={isOpenFunction} video_id={video_id} />
      <div className="w-full max-w-md bg-white rounded-lg shadow-md dark:bg-gray-800 dark:border dark:border-gray-700">
        <div className="p-6 sm:p-8 space-y-6">
          <h1 className="text-xl font-bold text-center text-gray-900 dark:text-white">
            Generate Video
          </h1>
          <form className="space-y-6" onSubmit={handleGenerate}>
            <div>
              <label
                htmlFor="message"
                className="block text-sm font-medium text-gray-900 dark:text-white"
              >
                Your prompt
              </label>
              <textarea
                name="message"
                id="message"
                value={formData.message}
                className={inputClassName}
                placeholder="Make me a video about potatoes"
                rows="6"
                required
                onChange={handleInputChange}
              ></textarea>
            </div>
            <div className="flex justify-center">
              <button
                type="button"
                className="text-center text-blue-600 dark:text-blue-400"
                onClick={() => setSettings(!settings)}
              >
                {settings ? "Hide settings" : "More settings"}
              </button>
            </div>
            {settings && (
              <div className="p-4 mt-4 bg-white rounded shadow-md dark:bg-gray-700">
                <div className="flex flex-col space-y-4">
                  {/* Template - Full width row */}
                  <div className="w-full">
                    <label
                      htmlFor="template"
                      className="block text-sm font-medium text-gray-900 dark:text-white"
                    >
                      Template
                    </label>
                    <select
                      name="template"
                      id="template"
                      value={formData.template}
                      className={inputClassName}
                      onChange={handleInputChange}
                    >
                      <option value="">None</option>
                      {templates?.map((template) => (
                        <option key={template.id} value={template.id}>
                          {template.title}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Target Audience & Genre row */}
                  <div className="flex space-x-4">
                    <div className="w-1/2">
                      <label
                        htmlFor="target_audience"
                        className="block text-sm font-medium text-gray-900 dark:text-white"
                      >
                        Target Audience
                      </label>
                      <input
                        name="target_audience"
                        type="text"
                        id="target_audience"
                        value={formData.target_audience}
                        placeholder="Teens"
                        className={inputClassName}
                        onChange={handleInputChange}
                      />
                    </div>
                    <div className="w-1/2">
                      <label
                        htmlFor="genre"
                        className="block text-sm font-medium text-gray-900 dark:text-white"
                      >
                        Genre
                      </label>
                      <input
                        name="genre"
                        type="text"
                        id="genre"
                        value={formData.genre}
                        placeholder="Comedy"
                        className={inputClassName}
                        onChange={handleInputChange}
                      />
                    </div>
                  </div>

                  <div className="flex space-x-4">
                    <div className="w-1/2">
                      <label
                        htmlFor="avatar_selection"
                        className="block text-sm font-medium text-gray-900 dark:text-white"
                      >
                        Avatar
                      </label>
                      <select
                        name="avatar_selection"
                        id="avatar_selection"
                        value={formData.avatar_selection}
                        className={inputClassName}
                        onChange={handleInputChange}
                      >
                        <option value="">No Avatar</option>
                        {avatars?.map((avatar) => (
                          <option key={avatar.id} value={avatar.id}>
                            {avatar.name}
                          </option>
                        ))}
                      </select>

                      {!formData.avatar_selection && (
                        <div className="mt-4">
                          <label
                            htmlFor="voice_id"
                            className="block text-sm font-medium text-gray-900 dark:text-white"
                          >
                            Voice
                          </label>
                          <select
                            name="voice_id"
                            id="voice_id"
                            value={formData.voice_id}
                            className={inputClassName}
                            onChange={handleInputChange}
                          >
                            <option value="">Any voice</option>
                            {voices?.map((voice) => (
                              <option key={voice.id} value={voice.id}>
                                {voice.name}
                                {voice.provider ? ` (${voice.provider})` : ""}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>
                    <div className="w-1/2">
                      <label
                        htmlFor="gpt_model"
                        className="block text-sm font-medium text-gray-900 dark:text-white"
                      >
                        AI Model
                      </label>
                      <select
                        name="gpt_model"
                        id="gpt_model"
                        value={formData.gpt_model}
                        className={inputClassName}
                        onChange={handleInputChange}
                      >
                        <optgroup label="OpenAI">
                          <option value="gpt-5.4-mini">gpt-5.4-mini</option>
                          <option value="gpt-5.4">gpt-5.4</option>
                          <option value="gpt-5.4-nano">gpt-5.4-nano</option>
                          <option value="gpt-5.5">gpt-5.5</option>
                          <option value="gpt-5.6-luna">gpt-5.6-luna</option>
                          <option value="gpt-5.6-sol">gpt-5.6-sol</option>
                          <option value="gpt-5.6-terra">gpt-5.6-terra</option>
                          <option value="gpt-6-astra">gpt-6-astra</option>
                          <option value="gpt-5">gpt-5</option>
                          <option value="gpt-5-mini">gpt-5-mini</option>
                          <option value="gpt-5-nano">gpt-5-nano</option>
                          <option value="gpt-5.1">gpt-5.1</option>
                          <option value="gpt-5.2">gpt-5.2</option>
                          <option value="gpt-5.3-chat-latest">
                            gpt-5.3-chat-latest
                          </option>
                          <option value="gpt-4.1">gpt-4.1</option>
                          <option value="gpt-4.1-mini">gpt-4.1-mini</option>
                          <option value="gpt-4.1-nano">gpt-4.1-nano</option>
                          <option value="gpt-4o">gpt-4o</option>
                          <option value="gpt-4o-mini">gpt-4o-mini</option>
                          <option value="gpt-4-turbo">gpt-4-turbo</option>
                          <option value="gpt-4">gpt-4</option>
                          <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                          <option value="o3">o3</option>
                          <option value="o3-mini">o3-mini</option>
                          <option value="o4-mini">o4-mini</option>
                          <option value="o1">o1</option>
                        </optgroup>
                        <optgroup label="Anthropic">
                          <option value="claude-3-5-sonnet-20240620">
                            claude 3-5
                          </option>
                        </optgroup>
                        <optgroup label="Google">
                          <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                          <option value="gemini-1.5-flash">
                            gemini-1.5-flash
                          </option>
                          <option value="gemini-1.0-pro">gemini-1.0-pro</option>
                        </optgroup>
                      </select>
                    </div>
                  </div>
                  <div className="flex space-x-4">
                    <div className="w-1/2">
                      <label
                        htmlFor="image_mode"
                        className="block text-sm font-medium text-gray-900 dark:text-white"
                      >
                        Image Mode
                      </label>
                      <select
                        name="image_mode"
                        id="image_mode"
                        value={formData.image_mode}
                        className={inputClassName}
                        onChange={handleInputChange}
                      >
                        <option value="WEB">WEB</option>
                        <option value="AI">AI</option>
                      </select>
                    </div>
                    <div className="w-1/2">
                      <label
                        htmlFor="provider"
                        className="block text-sm font-medium text-gray-900 dark:text-white"
                      >
                        Provider
                      </label>
                      <select
                        name="provider"
                        id="provider"
                        value={formData.provider}
                        className={inputClassName}
                        onChange={handleInputChange}
                      >
                        {formData.image_mode === "AI" ? (
                          <>
                            <option value="DALL-E">OpenAI (gpt-image)</option>
                            <option value="sora">OpenAI Sora (video)</option>
                            <option value="midjourney">midjourney</option>
                            <option value="stable-diffusion">
                              stable-diffusion
                            </option>
                          </>
                        ) : (
                          <>
                            <option value="bing">bing</option>
                            <option value="google">google</option>
                          </>
                        )}
                      </select>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      name="narration"
                      type="checkbox"
                      id="narration"
                      checked={formData.narration}
                      onChange={handleInputChange}
                      className="w-4 h-4 text-blue-600 bg-gray-50 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                    />
                    <label
                      htmlFor="narration"
                      className="text-sm font-medium text-gray-900 dark:text-white"
                    >
                      Narration
                    </label>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      off = clips only, no voice or subtitles
                    </span>
                  </div>
                  <div>
                    <label
                      htmlFor="music"
                      className="block text-sm font-medium text-gray-900 dark:text-white"
                    >
                      Music
                    </label>
                    <input
                      type="url"
                      name="music"
                      id="music"
                      value={formData.music}
                      placeholder="https://www.youtube.com/watch?v=JaZgHHDS5x0&list=RDJaZgHHDS5x0"
                      className={inputClassName}
                      onChange={handleInputChange}
                    />
                  </div>
                </div>
              </div>
            )}
            <LoadingButton isLoading={isLoading} />
          </form>
        </div>
      </div>
    </div>
  );
};

export default Home;