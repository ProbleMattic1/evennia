"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { getNavState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

const linkClass =
  "block w-full truncate px-2 py-1 text-[12px] text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-cyan-400/90 dark:hover:bg-cyan-950/40 dark:hover:text-cyan-300";

function NavDivider() {
  return (
    <hr
      className="my-1.5 mx-1 border-0 border-t border-zinc-200 dark:border-cyan-900/50"
      aria-hidden
    />
  );
}

const sectionHeaderClass =
  "flex w-full cursor-pointer items-center justify-between gap-1 truncate px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-zinc-500 hover:text-zinc-700 dark:text-cyan-400 dark:hover:text-cyan-300";

function NavSection({
  title,
  open,
  onToggle,
  children,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <details open={open} className="group">
      <summary
        className={`${sectionHeaderClass} list-none [&::-webkit-details-marker]:hidden`}
        onClick={(e) => {
          e.preventDefault();
          onToggle();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onToggle();
          }
        }}
        role="button"
        tabIndex={0}
      >
        <span>{title}</span>
        <svg
          className="size-3 shrink-0 transition-transform group-open:rotate-90"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </summary>
      <div className="mt-0.5">{children}</div>
    </details>
  );
}

const SECTION_KEYS = ["places", "mines", "bases", "kiosks", "shops"] as const;

export function SiteNav() {
  const loader = useCallback(() => getNavState(), []);
  const { data, error, loading } = useUiResource(loader);

  const [sections, setSections] = useState({
    places: true,
    mines: true,
    bases: false,
    kiosks: true,
    shops: true,
  });

  const allOpen = SECTION_KEYS.every((k) => sections[k]);
  const toggleAllSections = useCallback(() => {
    setSections((prev) =>
      SECTION_KEYS.reduce(
        (acc, k) => ({ ...acc, [k]: !allOpen }),
        {} as typeof sections
      )
    );
  }, [allOpen]);

  const setSection = useCallback((key: keyof typeof sections, open: boolean) => {
    setSections((prev) => ({ ...prev, [key]: open }));
  }, []);

  return (
    <aside
      className="sticky top-0 flex h-screen w-28 shrink-0 flex-col border-r border-zinc-200 bg-zinc-50/80 py-2 dark:border-cyan-900/50 dark:bg-zinc-950/90"
      aria-label="Main"
    >
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-1">
        <div className={`${sectionHeaderClass} py-1`}>
          <Link href="/" className="min-w-0 flex-1 truncate no-underline" title="Home">
            Home
          </Link>
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              toggleAllSections();
            }}
            className="shrink-0 rounded p-0.5 hover:bg-zinc-100 dark:hover:bg-cyan-950/40"
            title={allOpen ? "Collapse all" : "Expand all"}
            aria-label={allOpen ? "Collapse all" : "Expand all"}
          >
            <svg
              className={`size-3 shrink-0 ${allOpen ? "rotate-90" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        <NavDivider />

        {error ? (
          <span className="px-2 py-1 text-[10px] text-red-600 dark:text-red-400">
            Shops unavailable
          </span>
        ) : loading || !data ? (
          <span className="px-2 py-1 text-[10px] text-zinc-400 dark:text-cyan-500/70">Loading…</span>
        ) : (
          <>
            {data.exits.length > 0 && (
              <>
                <NavSection
                  title="Shops"
                  open={sections.places}
                  onToggle={() => setSection("places", !sections.places)}
                >
                  {data.exits
                    .filter((ex) => ex.destination)
                    .map((ex) => (
                      <Link
                        key={`${ex.key}-${ex.destination}`}
                        href={`/play?room=${encodeURIComponent(ex.destination!)}`}
                        className={linkClass}
                        title={ex.label}
                      >
                        {ex.label}
                      </Link>
                    ))}
                </NavSection>
              </>
            )}

            {(data.mines ?? []).length > 0 && (
              <>
                <NavDivider />
                <NavSection
                  title="Mines"
                  open={sections.mines}
                  onToggle={() => setSection("mines", !sections.mines)}
                >
                  {(data.mines ?? [])
                    .filter((ex) => ex.destination)
                    .map((ex) => (
                      <Link
                        key={`mine-${ex.key}-${ex.destination}`}
                        href={`/play?room=${encodeURIComponent(ex.destination!)}`}
                        className={linkClass}
                        title={ex.label}
                      >
                        {ex.label}
                      </Link>
                    ))}
                </NavSection>
              </>
            )}

            <NavDivider />
            <NavSection
              title="Bases"
              open={sections.bases}
              onToggle={() => setSection("bases", !sections.bases)}
            >
              <span className="px-2 py-1 text-[10px] text-zinc-400 dark:text-cyan-500/70">
                None yet
              </span>
            </NavSection>

            {(data.kiosks ?? []).length > 0 && (
              <>
                <NavDivider />
                <NavSection
                  title="Services"
                  open={sections.kiosks}
                  onToggle={() => setSection("kiosks", !sections.kiosks)}
                >
                  {(data.kiosks ?? []).map((k) => (
                    <Link key={k.key} href={k.href} className={linkClass} title={k.label}>
                      {k.label}
                    </Link>
                  ))}
                </NavSection>
              </>
            )}

            {data.shops.length > 0 && (
              <>
                <NavDivider />
                <NavSection
                  title="Kiosks"
                  open={sections.shops}
                  onToggle={() => setSection("shops", !sections.shops)}
                >
                  {data.shops.map((s) => (
                    <Link
                      key={s.roomKey}
                      href={`/shop?room=${encodeURIComponent(s.roomKey)}`}
                      className={linkClass}
                      title={s.label}
                    >
                      {s.label}
                    </Link>
                  ))}
                </NavSection>
              </>
            )}
          </>
        )}
      </nav>
      <div className="shrink-0 border-t border-zinc-200 px-1 py-2 dark:border-cyan-900/50">
        <ThemeToggle />
      </div>
    </aside>
  );
}
