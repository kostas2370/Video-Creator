import { NavLink } from "react-router-dom";

export function VideoCreationMode() {
  return <nav aria-label="Video creation mode" className="mb-8 flex gap-2">
    {[["/", "Create with AI"], ["/manual/", "Manual video"]].map(([to, label]) => <NavLink key={to} to={to} end className={({ isActive }) => `rounded-xl px-4 py-2 text-sm font-medium ${isActive ? "bg-blue-50 font-semibold text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"}`}>{label}</NavLink>)}
  </nav>;
}
