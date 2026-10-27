import { useNavigate } from "react-router-dom";
import { Link, NavLink, useLocation } from "react-router-dom";
import { HiOutlineSquares2X2 } from "react-icons/hi2";
import { creationModes } from "../utils/creationModes";

export function VideoCreationMode() {
  const { pathname } = useLocation();
  return <>
    <div className="mb-5 grid grid-cols-[auto_minmax(0,1fr)] items-center gap-3 border-b border-gray-200 pb-4 sm:hidden dark:border-gray-700">
      <Link to="/" className="inline-flex min-h-11 items-center gap-2 rounded-lg px-2 text-sm font-medium text-gray-500 focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-gray-400"><HiOutlineSquares2X2 aria-hidden="true" className="h-4 w-4" />All tools</Link>
      <MobileModeSelect pathname={pathname} />
    </div>
    <nav aria-label="Video creation mode" className="mb-8 hidden sm:flex flex-wrap items-center gap-2 border-b border-gray-200 pb-4 dark:border-gray-700">
    <Link to="/" className="mr-1 inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-gray-400 dark:hover:bg-gray-800"><HiOutlineSquares2X2 aria-hidden="true" className="h-4 w-4" />All tools</Link>
    {creationModes.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to !== "/series/"} className={({ isActive }) => `inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${isActive ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" : "text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white"}`}>
      <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />{label}
    </NavLink>)}
  </nav></>;
}

function MobileModeSelect({ pathname }) {
  const navigate = useNavigate();
  const current = creationModes.find(mode => pathname === mode.to || pathname.startsWith(`${mode.to.replace(/\/$/, "")}/`));
  return <select aria-label="Video creation mode" value={current?.to || ""} onChange={event => navigate(event.target.value)} className="min-h-11 w-full min-w-0 rounded-xl border border-gray-200 bg-white px-3 text-gray-900 dark:border-gray-700 dark:bg-gray-800 dark:text-white">{!current && <option value="" disabled>Choose a tool</option>}{creationModes.map(({ to, label }) => <option key={to} value={to}>{label}</option>)}</select>;
}
