"use client";

import Link from "next/link";
import { useCallback } from "react";

import { getClaimsMarketState } from "@/lib/ui-api";
import type { ClaimsMarketClaim } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

const TIER_CLASSES: Record<string, { text: string; badge: string }> = {
  emerald: {
    text:  "text-emerald-600 dark:text-emerald-400",
    badge: "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-400 dark:ring-emerald-700/50",
  },
  amber: {
    text:  "text-amber-600 dark:text-amber-400",
    badge: "bg-amber-100 text-amber-800 ring-1 ring-amber-300 dark:bg-amber-950 dark:text-amber-400 dark:ring-amber-700/50",
  },
  zinc: {
    text:  "text-zinc-600 dark:text-zinc-400",
    badge: "bg-zinc-100 text-zinc-700 ring-1 ring-zinc-300 dark:bg-zinc-900 dark:text-zinc-400 dark:ring-zinc-700/50",
  },
};

function ClaimRow({ c }: { c: ClaimsMarketClaim }) {
  const t = TIER_CLASSES[c.richnessTierCls] ?? TIER_CLASSES.zinc;
  return (
    <tr className="border-b border-zinc-200 transition-colors hover:bg-zinc-100 dark:border-zinc-800/60 dark:hover:bg-zinc-800/30">
      <td className="py-1.5 pr-3">
        <span className={`font-mono text-sm font-semibold ${t.text}`}>{c.roomKey}</span>
      </td>
      <td className="py-1.5 pr-3">
        <span className={`rounded px-1.5 py-0.5 font-mono text-[12px] font-medium ${t.badge}`}>
          {c.richnessTier}
        </span>
      </td>
      <td className="py-1.5 pr-3 font-mono text-sm text-zinc-600 dark:text-zinc-500">{c.hazardLabel}</td>
      <td className="py-1.5 pr-3 text-right font-mono text-sm text-zinc-500 dark:text-zinc-400">
        {c.baseOutputTons.toFixed(1)} t
      </td>
      <td className="py-1.5 pr-3 font-mono text-[12px] text-zinc-600 dark:text-zinc-500">{c.resources}</td>
      <td className="py-1.5 pl-3">
        <Link
          href="/"
          className="font-mono text-[12px] text-zinc-500 underline hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200"
        >
          Sign in to claim
        </Link>
      </td>
    </tr>
  );
}

export default function ClaimsMarketPage() {
  const loader = useCallback(() => getClaimsMarketState(), []);
  const { data, error, loading } = useUiResource(loader);

  return (
    <main className="main-content">
      <header className="border-b border-zinc-200 py-3 dark:border-zinc-700">
        <div className="px-2">
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Claims Market</h1>
          <p className="mt-0.5 text-[12px] text-zinc-500 dark:text-zinc-400">
            Unclaimed mining sites. Buy a package at Mining Outfitters to receive a random claim.
          </p>
        </div>
      </header>

      <section className="mt-4 overflow-hidden rounded border border-zinc-200 bg-zinc-50 px-2 py-4 dark:border-zinc-700/60 dark:bg-zinc-950">
        <div className="-mx-2 mb-2 flex items-center justify-between border-b border-zinc-200 bg-zinc-100 px-3 py-2 dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="font-mono text-[12px] font-semibold uppercase tracking-widest text-zinc-600 dark:text-zinc-300">
            Available Claims — Unclaimed Sites
          </h2>
        </div>

        {error && (
          <p className="py-1.5 font-mono text-sm text-red-600 dark:text-red-400">Market unavailable: {error}</p>
        )}
        {loading && !data && (
          <p className="animate-pulse py-3 font-mono text-sm text-zinc-600 dark:text-zinc-500">Loading…</p>
        )}
        {data && data.claims.length > 0 && (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-zinc-200 dark:border-zinc-800">
                <th className="pb-1.5 font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600 text-left pr-3">
                  Location
                </th>
                <th className="pb-1.5 font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600 text-left pr-3">
                  Tier
                </th>
                <th className="pb-1.5 font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600 text-left pr-3">
                  Hazard
                </th>
                <th className="pb-1.5 font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600 text-right pr-3">
                  Base t
                </th>
                <th className="pb-1.5 font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600 text-left pr-3">
                  Resources
                </th>
                <th className="pb-1.5 font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600 text-left pl-3">
                  Action
                </th>
              </tr>
            </thead>
            <tbody>
              {data.claims.map((c) => (
                <ClaimRow key={c.siteKey} c={c} />
              ))}
            </tbody>
          </table>
        )}
        {data && data.claims.length === 0 && (
          <p className="py-3 font-mono text-sm text-zinc-600 dark:text-zinc-500">No unclaimed sites available.</p>
        )}
      </section>

      <p className="mt-4 px-2 text-[12px] text-zinc-500 dark:text-zinc-400">
        <Link
          href="/shop?room=Aurnom%20Mining%20Outfitters"
          className="underline"
        >
          Mining Outfitters
        </Link>
        {" "}— Purchase a package to receive a random claim. Jackpot chance for elite claims.
      </p>
    </main>
  );
}
