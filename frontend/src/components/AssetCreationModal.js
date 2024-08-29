import { CloseModalButton } from "./ui/CloseModalButton";
import { useState } from "react";
import { toast } from "react-toastify";
export function AssetCreationModal({
  showModal,
  setShowModal,
  nameh1,
  ApiCall,
  setItems
}) {
  const [name, setName] = useState("");
  const [file, setFile] = useState("");


  const onSubmit = (event) => {
    event.preventDefault();
    const formData = new FormData();
    formData.append("name", name);
    formData.append("file", file);


    ApiCall(formData).then((response) => {
      if (response) {
        toast.success(nameh1+ " got added successfully !");
        setItems((prevItems) => [...prevItems, response]);        
        setShowModal(false);
      }
    });
  };

  return (
    <>
      {showModal ? (
        <>
          <div
            id="crud-modal"
            tabindex="-1"
            aria-hidden="false"
            class=" overflow-y-auto overflow-x-hidden fixed h-screen  flex items-center z-50 justify-center w-full md:inset-0 ackdrop-filter backdrop-blur-md  max-h-full"
          >
            <div class="relative p-4 w-full max-w-md max-h-full">
              <div class="relative bg-white rounded-lg shadow dark:bg-gray-700">
                <div class="flex items-center justify-between p-4 md:p-5 border-b rounded-t dark:border-gray-600">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white text-center w-full">
                    Create {nameh1} :
                  </h3>
                  <CloseModalButton setShowModal={setShowModal} />
                </div>
                <form onSubmit={onSubmit} class="p-4 md:p-5">
                  <div class="grid gap-4 mb-4 grid-cols-2">
                    <div class="col-span-2">
                      <label
                        for="name"
                        class="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                      >
                        Name :
                      </label>
                      <input
                        type="text"
                        name="text"
                        id="text"
                        class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500 dark:focus:border-primary-500"
                        placeholder={nameh1 + " name"}
                        required=""
                        onChange={(e) => setName(e.target.value)}
                      ></input>
                    </div>
                  </div>

                  <div class="grid gap-4 mb-4 grid-cols-2">
                    <div class="col-span-2">
                      <label
                        for="name"
                        class="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                      >
                        Select File :
                      </label>

                      <input
                        accept="video/mp4,video/x-m4v,video/*"
                        type="file"
                        name="file"
                        id="url"
                        class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500 dark:focus:border-primary-500"
                        placeholder={nameh1 + " name"}
                        required=""
                        onChange={(e) => setFile(e.target.files[0])}
                      ></input>
                    </div>
                  </div>

                  <div className="flex justify-center">
                    <button
                      type="submit"
                      class="text-white inline-flex items-center bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
                    >
                      <svg
                        class="me-1 -ms-1 w-5 h-5"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          fill-rule="evenodd"
                          d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z"
                          clip-rule="evenodd"
                        ></path>
                      </svg>
                      Add new {nameh1}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </>
  );
}
