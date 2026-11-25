import { HiOutlineMoon, HiOutlineSun } from "react-icons/hi2";

export function LandingThemeToggle({ theme, toggleTheme }) {
  if (!toggleTheme) return null;
  return (
    <button
      type="button"
      className="landing-theme-toggle"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
    >
      {theme === "dark" ? (
        <HiOutlineSun aria-hidden="true" />
      ) : (
        <HiOutlineMoon aria-hidden="true" />
      )}
    </button>
  );
}
