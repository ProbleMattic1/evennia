"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import { SiteNavAside, SiteNavBody, SiteNavProvider } from "@/components/site-nav";
import { ThemeToggle } from "@/components/theme-toggle";

export function SiteShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const prevOpenRef = useRef(open);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open]);

  useEffect(() => {
    if (prevOpenRef.current && !open) {
      menuButtonRef.current?.focus();
    }
    prevOpenRef.current = open;
  }, [open]);

  return (
    <SiteNavProvider>
      <div className="mx-auto flex min-h-svh w-[85%] min-w-0 flex-1 flex-col lg:flex-row">
        <SiteNavAside />

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-40 flex items-center gap-2 border-b border-cyan-900/50 bg-zinc-950/95 px-3 py-2 backdrop-blur dark:border-cyan-900/50 dark:bg-zinc-950/95 lg:hidden">
            <button
              ref={menuButtonRef}
              type="button"
              className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg border border-cyan-700/50 text-cyan-300 dark:border-cyan-700/50 dark:text-cyan-300"
              aria-expanded={open}
              aria-controls="mobile-nav"
              onClick={() => setOpen(true)}
            >
              <span className="sr-only">Open menu</span>
              <svg
                className="size-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>
            <span className="truncate text-sm font-semibold text-zinc-100 dark:text-zinc-100">
              Aurnom
            </span>
          </header>

          {open ? (
            <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Site menu">
              <button
                type="button"
                className="absolute inset-0 bg-black/50"
                aria-label="Close menu"
                onClick={close}
              />
              <div
                id="mobile-nav"
                className="absolute inset-y-0 left-0 flex w-[min(100%,18rem)] flex-col border-r border-cyan-900/50 bg-zinc-950 shadow-xl dark:border-cyan-900/50 dark:bg-zinc-950"
              >
                <div className="flex items-center justify-end border-b border-cyan-900/50 p-2 dark:border-cyan-900/50">
                  <button
                    type="button"
                    className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-zinc-500 dark:text-cyan-400"
                    onClick={close}
                  >
                    <span className="sr-only">Close</span>
                    <svg
                      className="size-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
                <div className="min-h-0 flex-1 overflow-y-auto py-2">
                  <SiteNavBody onNavigate={close} />
                </div>
                <div className="shrink-0 border-t border-cyan-900/50 px-1 py-2 dark:border-cyan-900/50">
                  <ThemeToggle />
                </div>
              </div>
            </div>
          ) : null}

          <main className="min-w-0 flex-1">{children}</main>
        </div>
      </div>
    </SiteNavProvider>
  );
}
