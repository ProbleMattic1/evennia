"use client";

import Link from "next/link";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { getNavState, type NavState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

const linkClass =
  "block w-full truncate rounded-md px-3 py-2.5 text-sm text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-cyan-400/90 dark:hover:bg-cyan-950/40 dark:hover:text-cyan-300 lg:px-2 lg:py-1 lg:text-[12px] lg:rounded-none";

function NavDivider() {
  return (
    <hr
      className="my-1.5 mx-1 border-0 border-t border-zinc-200 dark:border-cyan-900/50"
      aria-hidden
    />
  );
}

const sectionHeaderClass =
  "flex w-full cursor-pointer items-center justify-between gap-1 truncate px-3 py-2 text-sm font-semibold uppercase tracking-wide text-zinc-500 hover:text-zinc-700 dark:text-cyan-400 dark:hover:text-cyan-300 lg:px-2 lg:py-1 lg:text-[11px]";

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

const SECTION_KEYS = ["places", "mines", "claims", "bases", "kiosks", "shops"] as const;

const NAV_SECTIONS_SESSION_KEY = "aurnom-nav-sections";

function defaultSections() {
  return {
    places: false,
    mines: false,
    claims: false,
    bases: false,
    kiosks: false,
    shops: false,
  };
}

type SectionsState = ReturnType<typeof defaultSections>;

function parseStoredSections(raw: string | null): SectionsState | null {
  if (!raw) return null;
  try {
    const o = JSON.parse(raw) as unknown;
    if (!o || typeof o !== "object") return null;
    const out = defaultSections();
    for (const k of SECTION_KEYS) {
      const v = (o as Record<string, unknown>)[k];
      if (typeof v !== "boolean") return null;
      out[k] = v;
    }
    return out;
  } catch {
    return null;
  }
}

type NavContextValue = {
  data: NavState | null;
  error: string | null;
  loading: boolean;
  sections: SectionsState;
  setSection: (key: keyof SectionsState, open: boolean) => void;
  toggleAllSections: () => void;
  allOpen: boolean;
  claimLinks: { label: string; href: string }[];
};

const SiteNavContext = createContext<NavContextValue | null>(null);

function useSiteNavContext() {
  const ctx = useContext(SiteNavContext);
  if (!ctx) throw new Error("useSiteNavContext must be used within SiteNavProvider");
  return ctx;
}

export function SiteNavProvider({ children }: { children: ReactNode }) {
  const loader = useCallback(() => getNavState(), []);
  const { data, error, loading } = useUiResource<NavState>(loader);

  const [sections, setSections] = useState<SectionsState>(() => defaultSections());
  const [sectionsHydrated, setSectionsHydrated] = useState(false);

  useEffect(() => {
    /* sessionStorage is only available after mount; avoids SSR/client mismatch on first paint. */
    /* eslint-disable react-hooks/set-state-in-effect */
    try {
      const parsed = parseStoredSections(sessionStorage.getItem(NAV_SECTIONS_SESSION_KEY));
      if (parsed) setSections(parsed);
    } catch {
      /* ignore */
    }
    setSectionsHydrated(true);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  useEffect(() => {
    if (!sectionsHydrated) return;
    try {
      sessionStorage.setItem(NAV_SECTIONS_SESSION_KEY, JSON.stringify(sections));
    } catch {
      /* ignore */
    }
  }, [sections, sectionsHydrated]);

  const allOpen = SECTION_KEYS.every((k) => sections[k]);
  const toggleAllSections = useCallback(() => {
    setSections(
      SECTION_KEYS.reduce(
        (acc, k) => ({ ...acc, [k]: !allOpen }),
        {} as SectionsState
      )
    );
  }, [allOpen]);

  const setSection = useCallback((key: keyof typeof sections, open: boolean) => {
    setSections((prev) => ({ ...prev, [key]: open }));
  }, []);

  const claimLinks = useMemo(
    () =>
      data?.claims?.length
        ? data.claims
        : [{ label: "Claims Market", href: "/claims-market" }],
    [data]
  );

  const value = useMemo<NavContextValue>(
    () => ({
      data,
      error,
      loading,
      sections,
      setSection,
      toggleAllSections,
      allOpen,
      claimLinks,
    }),
    [data, error, loading, sections, setSection, toggleAllSections, allOpen, claimLinks]
  );

  return <SiteNavContext.Provider value={value}>{children}</SiteNavContext.Provider>;
}

export function SiteNavBody({ onNavigate }: { onNavigate?: () => void }) {
  const {
    data,
    error,
    loading,
    sections,
    setSection,
    toggleAllSections,
    allOpen,
    claimLinks,
  } = useSiteNavContext();

  const afterNav = onNavigate ?? (() => {});

  return (
    <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-1">
      <div className={`${sectionHeaderClass} py-2 lg:py-1`}>
        <Link
          href="/"
          className="min-w-0 flex-1 truncate no-underline"
          title="Home"
          onClick={afterNav}
        >
          Home
        </Link>
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleAllSections();
          }}
          className="inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded hover:bg-zinc-100 lg:min-h-0 lg:min-w-0 lg:p-0.5 dark:hover:bg-cyan-950/40"
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
          {(data.kiosks ?? []).length > 0 && (
            <>
              <NavSection
                title="Services"
                open={sections.kiosks}
                onToggle={() => setSection("kiosks", !sections.kiosks)}
              >
                {(data.kiosks ?? []).map((k) => (
                  <Link
                    key={k.key}
                    href={k.href}
                    className={linkClass}
                    title={k.label}
                    onClick={afterNav}
                  >
                    {k.label}
                  </Link>
                ))}
              </NavSection>
            </>
          )}

          {data.exits.length > 0 && (
            <>
              <NavDivider />
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
                      onClick={afterNav}
                    >
                      {ex.label}
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
                    onClick={afterNav}
                  >
                    {s.label}
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
                      onClick={afterNav}
                    >
                      {ex.label}
                    </Link>
                  ))}
              </NavSection>
            </>
          )}

          <NavDivider />
          <NavSection
            title="Claims"
            open={sections.claims}
            onToggle={() => setSection("claims", !sections.claims)}
          >
            {claimLinks.map((c) => (
              <Link key={c.href} href={c.href} className={linkClass} title={c.label} onClick={afterNav}>
                {c.label}
              </Link>
            ))}
          </NavSection>

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
        </>
      )}
    </nav>
  );
}

export function SiteNavAside() {
  return (
    <aside
      className="sticky top-0 hidden h-svh w-56 shrink-0 flex-col border-r border-zinc-200 bg-zinc-50/80 py-2 lg:flex dark:border-cyan-900/50 dark:bg-zinc-950/90"
      aria-label="Main"
    >
      <SiteNavBody />
      <div className="shrink-0 border-t border-zinc-200 px-1 py-2 dark:border-cyan-900/50">
        <ThemeToggle />
      </div>
    </aside>
  );
}
