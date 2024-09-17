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
      <table className="min-w-full bg-white border border-gray-300">
        <thead>
          <tr className="bg-gray-100 border-b">
            <th className="text-left py-2 px-4 border-r">Name</th>
            <th className="text-center py-2 px-2 border-r w-20">Url</th>
            <th className="text-center py-2 px-2 border-r w-20">Actions</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((row, index) => (
            <tr key={index} className="border-b">
              <td className="py-2 px-4 border-r">{row.name}</td>
              <td className="py-2 px-4 border-r">
                <a target="_blank" href={row.file}>
                  {row.file}
                </a>
              </td>

              <td className="py-2 px-2 border-r">
                <div className="flex justify-center space-x-2">
                  <RiDeleteBin6Fill onClick={(e) => {setId(row.id); setShowDeleteModal(true)}} className="w-4 h-4 text-red-500 hover:text-red-300" />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
