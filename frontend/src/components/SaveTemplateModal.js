import React, { useState } from "react";
import { toast } from "react-toastify";
import ReactLoading from "react-loading";
import { createTemplate } from "../api/apiService";
import { CloseModalButton } from "./ui/CloseModalButton";

export const SaveTemplateModal = ({
  showModal,
  setShowModal,
  settings,
  onSaved,
}) => {
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event) => {
    event.preventDefault();

    if (title.trim() === "") {
      toast.error("Give the template a name first!");
      return;
    }

    setLoading(true);
    const response = await createTemplate({ ...settings, title: title.trim() });
    setLoading(false);

    if (!response.ok) {
      toast.error(response.message);
      return;
    }

    toast.success(`Saved "${response.template.title}" as a template`);
    setTitle("");
    setShowModal(false);

    if (onSaved) onSaved(response.template);
  };

  if (!showModal) {
    return null;
  }

  return (
    <div
      id="save-template-modal"
      tabIndex="-1"
      className="overflow-y-auto overflow-x-hidden fixed h-screen flex items-center z-50 justify-center w-full inset-0 backdrop-filter backdrop-blur-md max-h-full"
    >
      <div className="relative p-4 w-full max-w-md max-h-full">
        <div className="relative bg-white rounded-lg shadow dark:bg-gray-700">
          <div className="flex items-center justify-between p-4 md:p-5 border-b rounded-t dark:border-gray-600">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white text-center w-full">
              Save as template
            </h3>
            <CloseModalButton setShowModal={setShowModal} />
          </div>
          <form className="p-4 md:p-5" onSubmit={onSubmit}>
            <div className="mb-4">
              <label
                htmlFor="template_title"
                className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
              >
                Template name :
              </label>
              <input
                type="text"
                name="template_title"
                id="template_title"
                maxLength={50}
                autoFocus
                value={title}
                className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500 dark:focus:border-primary-500"
                placeholder="Shorts about cats"
                onChange={(e) => setTitle(e.target.value)}
              />
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Keeps the prompt and every setting below it, ready to pick
                again.
              </p>
            </div>
            <div className="flex justify-center">
              {!loading ? (
                <button
                  type="submit"
                  className="text-white inline-flex items-center bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
                >
                  Save template
                </button>
              ) : (
                <ReactLoading
                  type="spokes"
                  color="#0000FF"
                  height={100}
                  width={50}
                />
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
