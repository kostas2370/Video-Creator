import React from "react";

const labels = { intro: "Opening clip", outro: "Closing clip", avatar: "Presenter" };

export const AssetDropBox = ({ type, items = [], className = "", value, setValue, selectedFile, setSelectedFile }) => {
  const id = `${type}-asset`;
  const handleChange = (event) => {
    const selectedValue = event.target.value;
    setValue(selectedValue);
    setSelectedFile(items.find((item) => String(item.id) === selectedValue)?.file || "");
  };

  return (
    <div className={className}>
      <label htmlFor={id} className="mb-2 block text-sm font-semibold text-gray-800 dark:text-gray-100">
        {labels[type] || type}
      </label>
      <select
        id={id}
        name={id}
        value={value ?? ""}
        onChange={handleChange}
        className="w-full rounded-xl border border-gray-200 bg-white px-3.5 py-3 text-sm text-gray-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
      >
        <option value="">No {labels[type]?.toLowerCase() || type}</option>
        {items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select>
      {selectedFile ? (
        <div className="mt-3 overflow-hidden rounded-xl border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/50">
          {type === "avatar" ? (
            <img src={selectedFile} alt="Selected presenter preview" className="h-36 w-full object-contain p-2" />
          ) : (
            <video controls key={selectedFile} className="h-36 w-full bg-gray-950 object-contain">
              <source src={selectedFile} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          )}
        </div>
      ) : (
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">No {labels[type]?.toLowerCase() || type} selected.</p>
      )}
    </div>
  );
};
