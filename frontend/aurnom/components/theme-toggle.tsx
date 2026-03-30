"use client";

import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "theme";

function readIsDark(): boolean {
  if (typeof document === "undefined") {
    return false;
  }
  try {
    const s = localStorage.getItem(STORAGE_KEY);
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (s === "dark") return true;
    if (s === "light") return false;
    return prefersDark;
  } catch {
    return document.documentElement.classList.contains("dark");
  }
}

function subscribe(onChange: () => void) {
  if (typeof window === "undefined") {
    return () => {};
  }
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  mq.addEventListener("change", onChange);
  window.addEventListener("storage", onChange);
  return () => {
    mq.removeEventListener("change", onChange);
    window.removeEventListener("storage", onChange);
  };
}

export function ThemeToggle() {
  const dark = useSyncExternalStore(subscribe, readIsDark, () => false);

  const toggle = useCallback(() => {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem(STORAGE_KEY, next ? "dark" : "light");
    } catch {
      /* ignore */
    }
    window.dispatchEvent(new Event("storage"));
  }, []);

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
