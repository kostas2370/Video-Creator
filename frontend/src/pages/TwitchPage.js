import React, { useState, useEffect, useRef } from "react";
import { generateTwitchVideo } from "../api/apiService";
import { pollVideo } from "../api/pollVideo";
import { format } from "date-fns";
import { toast } from "react-toastify";
import { LoadingButton } from "../components/ui/LoadingButton";
import { ProceedModal } from "../components/ProceedModal";


const Twitch = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [video_id, setVideo_id]= useState("")
  const pollRef = useRef(null);

  // Stop watching if the user navigates away mid-generation.
  useEffect(() => () => pollRef.current?.cancel(), []);


  const [formData, setFormData] = useState({
    mode: "game",
    value: "",
    started_at: null,
    amt: 5,
  });


  const handleTwitchGenerate = async (e) => {
    e.preventDefault();
    if (formData.value.trim() === "") {
      toast.error("You need to add a value !");
      return;
    }
    setIsLoading(true);

    // 202 + an empty video: the clips are downloaded by a worker, so watch the id.
    const response = await generateTwitchVideo(formData);

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
    toast.success("Video got generated successfully !");
  };


  const handleInputChange = (event) => {
    const { name, value } = event.target;
    if (name === "started_at") {
      setFormData({ ...formData, [name]: format(value, "yyyy-MM-dd") });
      console.log(formData);
      return;
    }

    setFormData({ ...formData, [name]: value });
  };

  const isOpenFunction = (data) => {
    setOpen(data)
}

  return (
    <div>
      <ProceedModal open={open} setOpen={isOpenFunction} video_id={video_id}/>

      <br></br>
      <section className="bg-gray-50 dark:bg-gray-900 ">
        <div className="flex flex-col items-center  px-6 py-8 mx-auto md:h-screen lg:py-0 ">
          <div className="w-full bg-white rounded-lg shadow dark:border md:mt-0 sm:max-w-md xl:p-0 dark:bg-gray-800 dark:border-gray-700">
            <div className="p-6 space-y-2 md:space-y-6 sm:p-9">
              <h1 className="text-xl font-bold leading-tight tracking-tight text-gray-900 md:text-2xl dark:text-white text-center">
                Generate Twitch Video:
              </h1>
              <form className="space-y-4 md:space-y-3" onSubmit={handleTwitchGenerate}>
                <div>
                  <label
                    htmlFor="mode"
                    className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                  >
                    Select mode :
                  </label>
                  <select
                    name="mode"
                    id="mode"
                    className="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                    required=""
                    onChange={handleInputChange}
                  >
                    <option value="game">Game</option>
                    <option value="streamer">Streamer</option>
                  </select>
                </div>
                <div>
                  <label
                    htmlFor="value"
                    className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                  >
                    {formData.mode === "game"
                      ? "Pick a game : *"
                      : "Pick a streamer : *"}
                  </label>
                  <input
                    name="value"
                    type="text"
                    id="value"
                    placeholder={
                      formData.mode === "game"
                        ? "League of Legends"
                        : "Asmogold"
                    }
                    className="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                    onChange={handleInputChange}
                  ></input>
                </div>
                <div>
                  <label
                    htmlFor="value"
                    className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                  >
                    Start searching clips starting from :
                  </label>
                  <input
                    name="started_at"
                    type="date"
                    id="started_at"
                    className="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                    onChange={handleInputChange}
                  ></input>
                </div>
                <div>
                  <label
                    htmlFor="value"
                    className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                  >
                    Select the amount of clips you want have in your video :
                  </label>
                  <input
                    name="amt"
                    type="number"
                    id="amt"
                    min="1"
                    max="10"
                    defaultValue={5}
                    className="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                    onChange={handleInputChange}
                  ></input>
                </div>
                <LoadingButton isLoading = {isLoading} />
              </form>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Twitch;
