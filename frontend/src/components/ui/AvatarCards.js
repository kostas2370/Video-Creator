import React, { useState } from "react";
import { RiDeleteBin6Fill } from "react-icons/ri";
import { DeleteModal } from "../DeleteModal";
import { deleteAvatar } from "../../api/apiService";

export const Card = ({ imageSrc, title, audioSrc, id, setAvatars }) => {
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  return (
    <>
      {showDeleteModal && (
        <DeleteModal
          showModal={showDeleteModal}
          setShowModal={setShowDeleteModal}
          id={id}
          setItems={setAvatars}
          deleteFunction={deleteAvatar}
          name="avatar"
        />
      )}
      <div className="group relative flex h-full w-full flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-lg dark:border-gray-700 dark:bg-gray-800">
        <div className="relative aspect-[4/3] w-full overflow-hidden bg-gray-100 dark:bg-gray-900">
          <img
            src={imageSrc}
            alt={title}
            className="h-full w-full object-cover object-top transition duration-300 group-hover:scale-105"
          />
          <button
            type="button"
            aria-label={`Delete ${title}`}
            onClick={() => setShowDeleteModal(true)}
            className="absolute right-2 top-2 rounded-full bg-white/90 p-2 text-red-500 shadow transition hover:bg-white hover:text-red-600 focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-red-400 group-hover:opacity-100 dark:bg-gray-900/80 dark:hover:bg-gray-900"
          >
            <RiDeleteBin6Fill className="h-4 w-4" />
          </button>
        </div>

        <div className="flex flex-1 flex-col gap-3 p-5">
          <h2
            className="truncate text-base font-semibold text-gray-900 dark:text-white"
            title={title}
          >
            {title}
          </h2>
          {audioSrc ? <><p className="text-xs text-gray-500 dark:text-gray-400">Preview voice</p><audio aria-label={`${title} voice preview`} controls className="mt-auto h-10 w-full">
            <source src={audioSrc} type="audio/mpeg" />
            Your browser does not support the audio element.
          </audio></> : <p className="text-xs text-gray-400">No voice preview available</p>}
        </div>
      </div>
    </>
  );
};
