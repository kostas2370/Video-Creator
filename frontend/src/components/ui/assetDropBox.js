import React from "react";

export const AssetDropBox = ({ type, items, className, value, setValue,selectedFile, setSelectedFile }) => {


  const handleChange = (event) => {
    const selectedValue = event.target.value;
    setValue(selectedValue);
    if (selectedValue) {
      items.map((item) => {
        if (selectedValue === item.id.toString()) {
          setSelectedFile(item?.file);
        }
      });
    } else {
      setSelectedFile("");
    }
  };


  return (
    <>
      <div className={className}>
        <label
          htmlFor="intro"
          className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
        >
          {type} :
        </label>
        <select
          name="intro"
          value={value}
          className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500 dark:focus:border-primary-500"
          onChange={handleChange}
        >
          <option key="no_value" value="">
            No {type}
          </option>
          {items.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </div>

      <div className={className}>
        {selectedFile && type !== "avatar"? (
          <video controls key={selectedFile}>
            <source src={selectedFile} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        ) :<> {selectedFile && type === "avatar"?(<><img src={selectedFile} alt={"test"} className="w-full h-40 object-contain p-2" /></>):null}</>}
      </div>
    </>
  );
};
