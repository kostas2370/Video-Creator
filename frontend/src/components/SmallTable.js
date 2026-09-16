import { useState } from "react";
import { RiDeleteBin6Fill } from "react-icons/ri";
import { DeleteModal } from "./DeleteModal";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";

export function SmallTable({ data, setData, deleteFunction }) {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [id, setId] = useState(null);

  return (
    <>
      <DeleteModal showModal={showDeleteModal} setShowModal={setShowDeleteModal} id={id} setItems={setData} name="Intro" mode="normal" deleteFunction={deleteFunction} />
      <table className="min-w-full bg-white border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-600">
        <thead>
          <tr className="bg-gray-100 border-b dark:bg-gray-700 dark:border-gray-600">
            <th className="text-left py-2 px-4 border-r dark:border-gray-600">Name</th>
            <th className="text-center py-2 px-2 border-r w-20 dark:border-gray-600">Url</th>
            <th className="text-center py-2 px-2 border-r w-20 dark:border-gray-600">Actions</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((row, index) => (
            <tr key={index} className="border-b dark:border-gray-600">
              <td className="py-2 px-4 border-r dark:border-gray-600">{row.name}</td>
              <td className="py-2 px-4 border-r dark:border-gray-600 max-w-0">
                <a
                  target="_blank"
                  rel="noreferrer"
                  href={row.file}
                  className="block truncate text-blue-600 hover:underline dark:text-blue-400"
                  title={row.file}
                >
                  {row.file}
                </a>
              </td>

              <td className="py-2 px-2 border-r dark:border-gray-600">
                <div className="flex justify-center space-x-2">
                  <RiDeleteBin6Fill onClick={(e) => {setId(row.id); setShowDeleteModal(true)}} className="w-4 h-4 text-red-500 hover:text-red-300" />
                </div>
              </td>
            </tr>
          ))}
          {!data?.length && (
            <tr>
              <td
                colSpan={3}
                className="py-6 text-center text-gray-500 dark:text-gray-400"
              >
                Nothing here yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </>
  );
}
