import { Link, NavLink } from "react-router-dom";
import { HiOutlineSquares2X2 } from "react-icons/hi2";
import { creationModes } from "../utils/creationModes";

export function VideoCreationMode() {
  return <nav aria-label="Video creation mode" className="mb-8 flex flex-wrap items-center gap-2 border-b border-gray-200 pb-4 dark:border-gray-700">
    <Link to="/" className="mr-1 inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-gray-400 dark:hover:bg-gray-800"><HiOutlineSquares2X2 aria-hidden="true" className="h-4 w-4" />All tools</Link>
    {creationModes.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end className={({ isActive }) => `inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${isActive ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" : "text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white"}`}>
      <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />{label}
    </NavLink>)}
  </nav>;
}
