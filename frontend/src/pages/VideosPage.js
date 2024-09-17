import React, { useState, useEffect } from "react";
import { DefaultTable } from "../components/Table";
import { getVideos } from "../api/apiService";
import { Search } from "@rsuite/icons";
import { useSearchParams } from "react-router-dom";
import { useDebounce } from "../hooks/useDebounce";

export const Videos = () => {
  const [searchParam, setSearchParam] = useSearchParams();

  const [videos, setVideos] = useState([]);
  const [search, setSearch] = useState(searchParam.get("search") || "");
  const debouncedSearchTerm = useDebounce(search, 500);

  const [currentPage, setCurrentPage] = useState(searchParam.get("page") || 1);
  const [previousPage, setPreviousPage] = useState(null);
  const [nextPage, setNextPage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);


  const fetchVideos = async () => {
    setIsLoading(true);
    setVideos([])
    const response = await getVideos(debouncedSearchTerm, currentPage);
    if (response) {
      setVideos(response.results);
      setNextPage(response.next);
      setPreviousPage(response.previous);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    if (debouncedSearchTerm !== searchParam.get("search")) {
      setCurrentPage(1);
    }
    setSearchParam({ page: currentPage, search: debouncedSearchTerm });

    fetchVideos();
  }, [debouncedSearchTerm, currentPage]);

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  return (
    <>
      <div className="flex justify-end items-center mt-4 gap-4  mr-64  ">
        <div className="relative">
          <input
            type="text"
            placeholder="Search Videos"
            value={search}
            className="pl-12 w-64 px-9 py-2  border rounded-l-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="absolute inset-y-2 left-2 flex items-center pl-3 pointer-events-none">
            <Search className="text-gray-500" />
          </div>
        </div>
      </div>

      <div className="flex flex-col items-center  px-6 py-8 mx-auto md:h-3/5 lg:py-0  lg:h-3/5 w-3/4  mt-4">
      
          <DefaultTable data={videos} setVideos={setVideos} loaded={isLoading}/>
     
        <div className="flex flex-col-2 gap-8 mt-4 pb-4 ">
          {previousPage && !isLoading ? (
            <button
              className="bg-blue-700 text-white font-bold py-2 px-4 rounded-r-lg hover:bg-blue-700 focus:outline-none focus:ring-2 rounded-lg focus:ring-blue-600 h-12 w-22"
              onClick={() => handlePageChange(previousPage)}
            >
              Previous
            </button>
          ) : null}
          {nextPage && !isLoading ? (
            <button
              className="bg-blue-700 text-white font-bold py-2 px-4 rounded-r-lg hover:bg-blue-700 focus:outline-none focus:ring-2 rounded-lg focus:ring-blue-600 h-12 w-22"
              onClick={() => handlePageChange(nextPage)}
            >
              Next
            </button>
          ) : null}
        </div>
      </div>
    </>
  );
};
