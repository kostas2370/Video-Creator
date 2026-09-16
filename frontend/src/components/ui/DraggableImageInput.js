
import React, { useState } from "react";


export const Dropzone = ({ onUpload }) => {
    const [isDragActive, setIsDragActive] = useState(false);
    const [fileName, setFileName] = useState("")
  
    const handleDragEnter = () => {
      setIsDragActive(true);
    };
  
    const handleDragLeave = () => {
      setIsDragActive(false);
    };
  
    const handleDrop = (e) => {
      setIsDragActive(false);
      const files = Array.from(e.dataTransfer.files);
      onUpload(files[0]);
      setFileName(files[0].name)
    };
  
    return (
      <div
        className={`flex justify-center items-center w-4/4 h-4/4 border-2 border-dashed rounded-lg p-5 
          ${isDragActive ? "bg-sky-50 border-sky-400" : "border-gray-300"}`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <p
          className={`text-sm ${
            isDragActive ? "text-sky-800" : "text-gray-400"
          }  `}
        >
          {isDragActive
            && ("Leave Your File Here")
            ||  fileName === ""  ? "Drag and drop your files here "  : "You uploaded " + fileName} 
        </p>
      </div>
    );
  };
  
  export default Dropzone;