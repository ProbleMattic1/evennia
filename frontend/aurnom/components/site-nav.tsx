"use client";

import Link from "next/link";
import { useCallback } from "react";

import { getNavState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

const PRIMARY = [
  { href: "/", label: "Home" },
  { href: "/play", label: "Play" },
  { href: "/bank", label: "Bank" },
  { href: "/shipyard", label: "Shipyard" },
] as const;

const linkClass =
  "shrink-0 rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-800 transition hover:bg-zinc-100";

function Separator() {
  return <span className="mx-1 h-4 w-px shrink-0 bg-zinc-200" aria-hidden />;
}

export function SiteNav() {
  const loader = useCallback(() => getNavState(), []);
  const { data, error, loading } = useUiResource(loader);

  return (
    <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
      <div className="mx-auto w-full max-w-6xl px-4 py-2">
        <nav
          className="flex flex-nowrap items-center gap-1.5 overflow-x-auto"
          aria-label="Main"
        >
          {PRIMARY.map((item) => (
            <Link key={item.href} href={item.href} className={linkClass}>
              {item.label}
            </Link>
          ))}

          <Separator />

          {error ? (
            <span className="shrink-0 text-xs text-red-600">Places unavailable: {error}</span>
          ) : loading || !data ? (
            <span className="shrink-0 text-xs text-zinc-500">Loading places…</span>
          ) : (
            <>
              {data.exits.map((ex) =>
                ex.destination ? (
                  <Link
                    key={`${ex.key}-${ex.destination}`}
                    href={`/play?room=${encodeURIComponent(ex.destination)}`}
                    className={linkClass}
                  >
                    {ex.label}
                  </Link>
                ) : null,
              )}
              {data.exits.some((ex) => ex.destination) ? <Separator /> : null}
              {data.shops.map((s) => (
                <Link
                  key={s.roomKey}
                  href={`/shop?room=${encodeURIComponent(s.roomKey)}`}
                  className={linkClass}
                >
                  {s.label}
                </Link>
              ))}
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
