import React, { useState, useEffect } from "react";
import { Search } from "@rsuite/icons";
import { getAvatars } from "../api/apiService";
import { Card } from "../components/ui/AvatarCards";
import { AvatarCreationModal } from "../components/AvatarCreationModal";
import { useDebounce } from "../hooks/useDebounce";

export const Avatar = () => {
  const [avatars, setAvatars] = useState([]);
  const [search, setSearch] = useState([]);
  const [showModal, setshowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const debouncedSearchTerm = useDebounce(search, 500);




  useEffect(() => {
    setLoading(true)

    getAvatars(search).then((response) => {
      setAvatars(response);
      setLoading(false)

    });
  }, [debouncedSearchTerm])
 

  return (
    <>
      <div className="container mx-auto px-4">
        <AvatarCreationModal
          showModal={showModal}
          setShowModal={setshowModal}
          avatars={avatars}
          setAvatars={setAvatars}
        />

        {/* Search bar and Create button */}
        <div className="flex justify-end items-center mt-4 gap-2 backdrop-filter ">
          <div className="relative">
            <input
              type="text"
              placeholder="Search Avatars"
              className="pl-12 w-64 px-9 py-2  border rounded-l-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
              onChange={(e) => setSearch(e.target.value)}
            />
            <div className="absolute inset-y-2 left-2 flex items-center pl-3 pointer-events-none">
              <Search
                className="text-gray-500"
                
              />
            </div>
          </div>
   
          <button
            onClick={(e) => setshowModal(true)}
            className="bg-gray-800 text-white font-bold py-2 px-8 rounded-r-lg hover:bg-blue-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 "
          >
            Create new avatar
          </button>
        </div>
      </div>
      
      <div className="bg-gray-100 p-2 grid  grid-cols-1  sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 ml-6 mr-6 mt-4 ">
        
        {!loading ? (<>{avatars?.length > 0 ? (
          <>
            {avatars?.map((avatar) => (
              <div className="mt-4 ml-20">
                <Card
                  imageSrc={avatar.file}
                  title={avatar.name}
                  audioSrc={avatar.sample}
                  id={avatar.id}
                  avatars={avatars}
                  setAvatars={setAvatars}
                />
              </div>
            ))}
          </>
        ) : (
          <>
            <p class="text-center text-lg text-gray-700 className= mt-4 ml-20">
              Avatars are empty,{" "}
              <span class="text-blue-500 font-semibold">
                create your avatars!
              </span>
            </p>
          </>
        )}</>) : null}
        
      </div>
    </>
  );
};
