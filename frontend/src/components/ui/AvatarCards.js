import React, { useState, useEffect } from "react";
import { RiDeleteBin6Fill } from "react-icons/ri";
import { DeleteModal } from "../DeleteModal";
import { deleteAvatar } from "../../api/apiService";

export const Card = ({ imageSrc, title, audioSrc, id , avatars, setAvatars }) => {
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
      <div className="group relative flex h-full w-full max-w-xs flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-lg dark:border-gray-700 dark:bg-gray-800">
        {/* A fixed ratio keeps every card the same height whatever the source image
            is, and object-top crops from the feet rather than the face. */}
        <div className="relative aspect-[4/3] w-full overflow-hidden bg-gray-100 dark:bg-gray-900">
          <img
            src={imageSrc}
            alt={title}
            className="h-full w-full object-cover object-top transition duration-300 group-hover:scale-105"
          />
          {/* A real button, so it is keyboard reachable — it used to be a bare icon
              with an onClick. Revealed on hover, but always visible once focused. */}
          <button
            type="button"
            aria-label={`Delete ${title}`}
            onClick={() => setShowDeleteModal(true)}
            className="absolute right-2 top-2 rounded-full bg-white/90 p-2 text-red-500 opacity-0 shadow transition hover:bg-white hover:text-red-600 focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-red-400 group-hover:opacity-100 dark:bg-gray-900/80 dark:hover:bg-gray-900"
          >
            <RiDeleteBin6Fill className="h-4 w-4" />
          </button>
        </div>

        <div className="flex flex-1 flex-col gap-3 p-4">
          <h2
            className="truncate text-base font-semibold text-gray-900 dark:text-white"
            title={title}
          >
            {title}
          </h2>
          <audio controls className="mt-auto w-full">
            <source src={audioSrc} type="audio/mpeg" />
            Your browser does not support the audio element.
          </audio>
        </div>
      </div>
    </>
  );
};
