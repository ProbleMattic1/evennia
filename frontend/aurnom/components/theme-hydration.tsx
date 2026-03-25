"use client";

import { useLayoutEffect } from "react";

const STORAGE_KEY = "theme";

function applyStoredTheme() {
  try {
    const s = localStorage.getItem(STORAGE_KEY);
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const dark = s === "dark" || (s !== "light" && prefersDark);
    document.documentElement.classList.toggle("dark", dark);
  } catch {
    /* private mode / blocked storage */
  }
}

/**
 * Re-applies theme from localStorage after React hydrates. The inline script in
 * layout runs first, but Next may reset <html> className during hydration and
 * drop `dark`; this runs in useLayoutEffect before paint.
 */
export function ThemeHydration() {
  useLayoutEffect(() => {
    applyStoredTheme();
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY || e.key === null) {
        applyStoredTheme();
      }
    };
    const onMq = () => {
      if (localStorage.getItem(STORAGE_KEY) == null) {
        applyStoredTheme();
      }
    };
    window.addEventListener("storage", onStorage);
    mq.addEventListener("change", onMq);
    return () => {
      window.removeEventListener("storage", onStorage);
      mq.removeEventListener("change", onMq);
    };
  }, []);

  return null;
}
