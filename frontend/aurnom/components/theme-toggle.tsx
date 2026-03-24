"use client";

import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  const toggle = () => {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
    setDark(next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      className="block w-full rounded px-2 py-1 text-left text-[12px] text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-cyan-400/90 dark:hover:bg-cyan-950/40 dark:hover:text-cyan-300"
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {dark ? "☀ Light" : "☽ Dark"}
    </button>
  );
}
