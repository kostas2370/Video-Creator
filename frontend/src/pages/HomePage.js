import React, { useState, useEffect } from "react";
import { getAvatars } from "../api/apiService";
import { toast } from "react-toastify";
import { generateVideo } from "../api/apiService";
import { LoadingButton } from "../components/ui/LoadingButton";
import { ProceedModal } from "../components/ProceedModal";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";

const Home = () => {
  const isOpenFunction = (data) => {
    setOpen(data);
  };
  const [avatars, setAvatars] = useState([]);
  const [settings, setSettings] = useState(false);
  const [open, setOpen] = useState(false);
  const [video_id, setVideo_id] = useState("");
  const [isLoading, setIsLoading] = useState(false);


  const [formData, setFormData] = useState({
    template_id: "",
    avatar_selection: "no_avatar",
    message: "",
    target_audience: "",
    images: "WEB",
    gpt_model: "gpt-4o",
    style: "natural",
    music: "",
    provider: "",
    subtitles: true,
    avatar_position:"top,left"
  });

 const axiosPrivateInstance = useAxiosPrivate()

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    if (name === "images") {
      setFormData((prevData) => ({
        ...prevData,
        [name]: value,
        provider: value === "AI" ? "DALL-E" : "bing",
      }));
    } else {
      setFormData({ ...formData, [name]: value });
    }
  };

  useEffect(() => {
    const fetchOptions = async () => {
      axiosPrivateInstance.get("avatars/").then((response) => {
        setAvatars(response.data);
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

    generateVideo(formData).then((response) => {
      if (response) {
        setVideo_id(response.video.id);
        setOpen(true);
        toast.success("Video generated successfully!");
      }
      setIsLoading(false);
    });
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
                className="w-full p-2.5 mt-2 bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
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
                        placeholder="Teens"
                        className="w-full p-2.5 mt-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                        onChange={handleInputChange}
                      />
                    </div>
                    <div className="w-1/2">
                      <label
                        htmlFor="template_id"
                        className="block text-sm font-medium text-gray-900 dark:text-white"
                      >
                        Genre
                      </label>
                      <input
                        name="template_id"
                        type="text"
                        id="template_id"
                        placeholder="Comedy"
                        className="w-full p-2.5 mt-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
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
                        className="w-full p-2.5 mt-2 bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                        onChange={handleInputChange}
                      >
                        <option value="no_avatar">No Avatar</option>
                        {avatars?.map((avatar) => (
                          <option key={avatar.id} value={avatar.id}>
                            {avatar.name}
                          </option>
                        ))}
                      </select>
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
                        className="w-full p-2.5 mt-2 bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                        onChange={handleInputChange}
                      >
                        <option value="gpt-4o">gpt-4o</option>
                        <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                        <option value="gpt-4">gpt-4</option>
                        <option value="claude-3-5-sonnet-20240620">
                          claude 3-5
                        </option>
                        <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                        <option value="gemini-1.5-flash">
                          gemini-1.5-flash
                        </option>
                        <option value="gemini-1.0-pro">gemini-1.0-pro</option>
                      </select>
                    </div>
                  </div>
                  <div className="flex space-x-4">
                    <div className="w-1/2">
                      <label
                        htmlFor="images"
                        className="block text-sm font-medium text-gray-900 dark:text-white"
                      >
                        Image Mode
                      </label>
                      <select
                        name="images"
                        id="images"
                        className="w-full p-2.5 mt-2 bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
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
                        className="w-full p-2.5 mt-2 bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                        onChange={handleInputChange}
                      >
                        {formData.images === "AI" ? (
                          <>
                            <option value="DALL-E">DALL-E</option>
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
                      placeholder="https://www.youtube.com/watch?v=JaZgHHDS5x0&list=RDJaZgHHDS5x0"
                      className="w-full p-2.5 mt-2 bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
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
