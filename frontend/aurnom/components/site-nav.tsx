"use client";

import Link from "next/link";
import { useCallback } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { getNavState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

const PRIMARY = [
  { href: "/", label: "Home" },
  { href: "/play", label: "Play" },
] as const;

const linkClass =
  "block w-full truncate px-2 py-1 text-[12px] text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200";

function NavDivider() {
  return (
    <hr
      className="my-1.5 mx-1 border-0 border-t border-zinc-200 dark:border-zinc-700"
      aria-hidden
    />
  );
}

export function SiteNav() {
  const loader = useCallback(() => getNavState(), []);
  const { data, error, loading } = useUiResource(loader);

  return (
    <aside
      className="sticky top-0 flex h-screen w-28 shrink-0 flex-col border-r border-zinc-200 bg-zinc-50/80 py-2 dark:border-zinc-700 dark:bg-zinc-900/80"
      aria-label="Main"
    >
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-1">
        {PRIMARY.map((item) => (
          <Link key={item.href} href={item.href} className={linkClass} title={item.label}>
            {item.label}
          </Link>
        ))}

        <NavDivider />

        {error ? (
          <span className="px-2 py-1 text-[10px] text-red-600 dark:text-red-400">
            Places unavailable
          </span>
        ) : loading || !data ? (
          <span className="px-2 py-1 text-[10px] text-zinc-400 dark:text-zinc-500">Loading…</span>
        ) : (
          <>
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

            {(data.kiosks ?? []).length > 0 && (
              <>
                <NavDivider />
                {(data.kiosks ?? []).map((k) => (
                  <Link key={k.key} href={k.href} className={linkClass} title={k.label}>
                    {k.label}
                  </Link>
                ))}
              </>
            )}

            {data.shops.length > 0 && (
              <>
                <NavDivider />
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
              </>
            )}
          </>
        )}
      </nav>
      <div className="shrink-0 border-t border-zinc-200 px-1 py-2 dark:border-zinc-700">
        <ThemeToggle />
      </div>
    </aside>
  );
}
