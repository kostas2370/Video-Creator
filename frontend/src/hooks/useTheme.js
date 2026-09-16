import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "theme";

function storedTheme() {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === "dark" || stored === "light" ? stored : null;
  } catch (error) {
    // Safari in private mode throws on localStorage rather than returning null.
    return null;
  }
}

/** The theme to start from: a previous choice if there is one, else the OS setting. */
export function initialTheme() {
  return (
    storedTheme() ||
    (window.matchMedia?.("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light")
  );
}

/** Tailwind runs in darkMode: "class", so this class is what switches the theme. */
export function applyTheme(theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export default function useTheme() {
  const [theme, setTheme] = useState(initialTheme);

  useEffect(() => applyTheme(theme), [theme]);

  // Keep following the OS until the user picks a side. Nothing is written to storage
  // before then — persisting on mount would make this listener think a choice had
  // already been made and silently stop the app tracking the system setting.
  useEffect(() => {
    if (storedTheme()) return;

    const query = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!query) return;

    const onChange = (event) => setTheme(event.matches ? "dark" : "light");
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch (error) {
        // Not remembering the choice is not worth breaking the page over.
      }
      return next;
    });
  }, []);

  return { theme, toggleTheme };
}
