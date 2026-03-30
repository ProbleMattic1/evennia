"use client";

import { useLayoutEffect, useState } from "react";

const STORAGE_KEY = "theme";

function readIsDark() {
  if (typeof document === "undefined") {
    return false;
  }
  try {
    const s = localStorage.getItem(STORAGE_KEY);
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (s === "dark") {
      return true;
    }
    if (s === "light") {
      return false;
    }
    return prefersDark;
  } catch {
    return document.documentElement.classList.contains("dark");
  }
}

export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useLayoutEffect(() => {
    setDark(readIsDark());
  }, []);

  const toggle = () => {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem(STORAGE_KEY, next ? "dark" : "light");
    } catch {
      /* ignore */
    }
    setDark(next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      className="block w-full rounded px-2 py-1 text-left text-xs text-zinc-700 hover:bg-zinc-100 hover:text-zinc-900 dark:text-ui-soft dark:hover:bg-cyan-950/40 dark:hover:text-cyber-cyan"
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {dark ? "☀ Light" : "☽ Dark"}
    </button>
  );
}
