import React, { useState } from "react";
import { generateTwitchVideo } from "../api/apiService";
import { format } from "date-fns";
import { toast } from "react-toastify";
import { LoadingButton } from "../components/ui/LoadingButton";
import { ProceedModal } from "../components/ProceedModal";


const Twitch = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [video_id, setVideo_id]= useState("")


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
    generateTwitchVideo(formData).then((response) => {
      if (response) {
        setVideo_id(response.video.id)
        setOpen(true)

        toast.success("Video got generated successfully !");
      } 
      setIsLoading(false);
    });
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
      <section class="bg-gray-50 dark:bg-gray-900 ">
        <div class="flex flex-col items-center  px-6 py-8 mx-auto md:h-screen lg:py-0 ">
          <div class="w-full bg-white rounded-lg shadow dark:border md:mt-0 sm:max-w-md xl:p-0 dark:bg-gray-800 dark:border-gray-700">
            <div class="p-6 space-y-2 md:space-y-6 sm:p-9">
              <h1 class="text-xl font-bold leading-tight tracking-tight text-gray-900 md:text-2xl dark:text-white text-center">
                Generate Twitch Video:
              </h1>
              <form class="space-y-4 md:space-y-3" onSubmit={handleTwitchGenerate}>
                <div>
                  <label
                    for="mode"
                    class="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                  >
                    Select mode :
                  </label>
                  <select
                    name="mode"
                    id="mode"
                    class="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                    required=""
                    onChange={handleInputChange}
                  >
                    <option value="game">Game</option>
                    <option value="streamer">Streamer</option>
                  </select>
                </div>
                <div>
                  <label
                    for="value"
                    class="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
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
                    class="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                    onChange={handleInputChange}
                  ></input>
                </div>
                <div>
                  <label
                    for="value"
                    class="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                  >
                    Start searching clips starting from :
                  </label>
                  <input
                    name="started_at"
                    type="date"
                    id="started_at"
                    class="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                    onChange={handleInputChange}
                  ></input>
                </div>
                <div>
                  <label
                    for="value"
                    class="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
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
                    class="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
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
