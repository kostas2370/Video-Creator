import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "theme";

function storedTheme() {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === "dark" || stored === "light" ? stored : null;
  } catch (error) {
    return null;
  }
}

export function initialTheme() {
  return (
    storedTheme() ||
    (window.matchMedia?.("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light")
  );
}

export function applyTheme(theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export default function useTheme() {
  const [theme, setTheme] = useState(initialTheme);

  useEffect(() => applyTheme(theme), [theme]);

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
      }
      return next;
    });
  }, []);

  return { theme, toggleTheme };
}
