import { useEffect } from "react";
import { Link, NavLink } from "react-router-dom";
import { HiOutlineBookOpen, HiOutlineSparkles } from "react-icons/hi2";

export const linkStyle =
  "font-semibold text-blue-600 underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-300";
export const panelStyle =
  "rounded-2xl border border-gray-200 bg-white p-5 sm:p-7 dark:border-gray-700 dark:bg-gray-800";

export function HelpLayout({
  title,
  description,
  eyebrow = "Learn & explore",
  children,
}) {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = `${title} · Viddie`;
    if (!window.location.hash) window.scrollTo(0, 0);
    return () => {
      document.title = previousTitle;
    };
  }, [title]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <Link to="/" className={`text-sm ${linkStyle}`}>
        ← Viddie home
      </Link>
      <header className="mb-8 mt-7 rounded-3xl border border-blue-100 bg-blue-50 p-6 sm:p-10 dark:border-gray-700 dark:bg-gray-800">
        <p className="text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-300">
          {eyebrow}
        </p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
          {title}
        </h1>
        <p className="mt-3 max-w-2xl leading-relaxed text-gray-500 dark:text-gray-400">
          {description}
        </p>
        <nav aria-label="Help pages" className="mt-6 flex flex-wrap gap-2">
          {[
            { to: "/guide/", label: "Guide", icon: HiOutlineBookOpen },
            { to: "/whats-new/", label: "What’s new", icon: HiOutlineSparkles },
          ].map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end
              className={({ isActive }) =>
                `inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${isActive ? "bg-blue-600 text-white" : "bg-white text-gray-600 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"}`
              }
            >
              <Icon aria-hidden="true" className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      {children}
    </main>
  );
}
