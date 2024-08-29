import { Search } from "@rsuite/icons";


export const SearchInput = ({ placeholder, onChange }) => {
  return (
    <div className="relative">
      <input
        type="text"
        placeholder={placeholder}
        className="pl-12 w-64 px-9 py-2 border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
      />
      <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
        <Search className="text-gray-500" />
      </div>
    </div>
  );
};
