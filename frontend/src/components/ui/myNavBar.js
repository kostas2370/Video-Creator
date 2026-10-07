import React, { useEffect, useState } from "react";
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { RiMoonLine, RiSunLine } from "react-icons/ri";
import { HiOutlineBars3, HiOutlineXMark, HiOutlineUserCircle, HiOutlineChevronDown, HiOutlineArrowRightOnRectangle, HiOutlineKey, HiOutlineFilm, HiOutlineSparkles, HiOutlineSquares2X2, HiOutlineUserGroup } from "react-icons/hi2";
import { NotificationBell } from "./NotificationBell";
import useLogout from "../../hooks/useLogout";

const destinations = [
  { to: "/", label: "Generate", icon: HiOutlineSparkles },
  { to: "/videos", label: "My videos", icon: HiOutlineFilm },
  { to: "/avatars", label: "Avatars", icon: HiOutlineUserGroup },
  { to: "/assets", label: "My assets", icon: HiOutlineSquares2X2 },
  { to: "/api-keys", label: "Providers", icon: HiOutlineKey },
];
const iconButton = "rounded-xl p-2 text-gray-500 transition hover:bg-gray-100 hover:text-gray-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white";

function Navbar({ theme, toggleTheme }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const logout = useLogout();
  useEffect(() => setIsMenuOpen(false), [location.pathname]);
  useEffect(() => {
    if (!isMenuOpen) return;
    const close = event => { if (event.key === "Escape") setIsMenuOpen(false); };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [isMenuOpen]);

  const links = mobile => destinations.map(({ to, label, icon: Icon }) => (
    <NavLink key={to} to={to} end={to === "/"} onClick={() => setIsMenuOpen(false)} className={({ isActive }) => `flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${mobile ? "" : "whitespace-nowrap"} ${isActive ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" : "text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white"}`}>
      <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />{label}
    </NavLink>
  ));

  return (
    <header className="border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
        <NavLink to="/" aria-label="Video Creator home" className="flex shrink-0 items-center gap-2.5 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm"><HiOutlineFilm aria-hidden="true" className="h-5 w-5" /></span>
          <span className="hidden text-base font-bold tracking-tight text-gray-900 sm:block dark:text-white">Video Creator</span>
        </NavLink>
        <nav aria-label="Main navigation" className="hidden items-center gap-1 xl:flex">{links(false)}</nav>
        <div className="flex shrink-0 items-center gap-1">
          <button type="button" onClick={toggleTheme} aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"} className={iconButton}>{theme === "dark" ? <RiSunLine className="h-5 w-5" /> : <RiMoonLine className="h-5 w-5" />}</button>
          <NotificationBell />
          <Menu as="div" className="relative">
            <MenuButton aria-label="Account menu" className={`${iconButton} flex items-center gap-1`}><HiOutlineUserCircle className="h-6 w-6" /><HiOutlineChevronDown className="hidden h-3 w-3 sm:block" /></MenuButton>
            <MenuItems anchor="bottom end" className="z-50 mt-3 w-60 rounded-2xl border border-gray-200 bg-white p-2 shadow-xl focus:outline-none dark:border-gray-700 dark:bg-gray-800">
              <p className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-400">Account</p>
              <MenuItem><NavLink to="/api-keys/" className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-gray-700 data-[focus]:bg-gray-50 dark:text-gray-200 dark:data-[focus]:bg-gray-700"><HiOutlineKey className="h-4 w-4 text-blue-500" />API keys and providers</NavLink></MenuItem>
              <div className="my-1 border-t border-gray-100 dark:border-gray-700" />
              <MenuItem><button type="button" onClick={async () => { if (await logout()) navigate("/login/"); }} className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm text-gray-500 data-[focus]:bg-gray-50 dark:text-gray-300 dark:data-[focus]:bg-gray-700"><HiOutlineArrowRightOnRectangle className="h-4 w-4" />Sign out</button></MenuItem>
            </MenuItems>
          </Menu>
          <button type="button" aria-label={isMenuOpen ? "Close main menu" : "Open main menu"} aria-controls="mobile-menu" aria-expanded={isMenuOpen} onClick={() => setIsMenuOpen(open => !open)} className={`${iconButton} xl:hidden`}>{isMenuOpen ? <HiOutlineXMark className="h-6 w-6" /> : <HiOutlineBars3 className="h-6 w-6" />}</button>
        </div>
      </div>
      {isMenuOpen && <nav id="mobile-menu" aria-label="Mobile navigation" className="border-t border-gray-100 px-4 py-3 xl:hidden dark:border-gray-800"><div className="mx-auto grid max-w-7xl gap-1 sm:grid-cols-2">{links(true)}</div></nav>}
    </header>
  );
}
export default Navbar;
