import { NavLink } from "react-router-dom";
import { HiOutlineSparkles, HiOutlineFilm } from "react-icons/hi2";

const modes = [
  { to: "/", label: "Create with AI", description: "Turn an idea into a script, voice, and visuals.", icon: HiOutlineSparkles },
  { to: "/manual/", label: "Manual video", description: "Edit your own photos, clips, and audio.", icon: HiOutlineFilm },
];

export function VideoCreationMode() {
  return <nav aria-label="Video creation mode" className="mb-8 grid gap-3 sm:grid-cols-2">
    {modes.map(({ to, label, description, icon: Icon }) => <NavLink key={to} to={to} end className={({ isActive }) => `flex items-start gap-3 rounded-2xl border p-4 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${isActive ? "border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300" : "border-gray-200 bg-white text-gray-600 hover:border-blue-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"}`}>
      <Icon aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
      <span><span className="block text-sm font-semibold">{label}</span><span className="mt-1 block text-xs leading-relaxed text-gray-500 dark:text-gray-400">{description}</span></span>
    </NavLink>)}
  </nav>;
}
