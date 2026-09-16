import React from "react";
import ReactLoading from "react-loading";

import "react-toastify/dist/ReactToastify.css";
export const LoadingButton = (props) => {
  return (
    <>
      {!props.isLoading ? (
        <button
          type="submit"
          className="w-full text-white bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
        >
          Generate Video
        </button>
      ) : (
        <div className="flex justify-center  ">
          <ReactLoading type="spokes" color="#0000FF" height={100} width={50} />
        </div>
      )}
    </>
  );
};

