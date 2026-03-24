"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import {
  getClaimsMarketState,
  getDashboardState,
  purchaseClaimDeed,
} from "@/lib/ui-api";
import type { ClaimsMarketClaim } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";
import { Countdown } from "@/components/countdown";

const TIER_CLASSES: Record<string, { text: string; badge: string }> = {
  sky: {
    text:  "text-sky-600 dark:text-sky-400",
    badge: "bg-sky-100 text-sky-800 ring-1 ring-sky-300 dark:bg-sky-950 dark:text-sky-400 dark:ring-sky-700/50",
  },
  emerald: {
    text:  "text-emerald-600 dark:text-emerald-400",
    badge: "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-400 dark:ring-emerald-700/50",
  },
  amber: {
    text:  "text-amber-600 dark:text-amber-400",
    badge: "bg-amber-100 text-amber-800 ring-1 ring-amber-300 dark:bg-amber-950 dark:text-amber-400 dark:ring-amber-700/50",
  },
  violet: {
    text:  "text-violet-600 dark:text-violet-400",
    badge: "bg-violet-100 text-violet-800 ring-1 ring-violet-300 dark:bg-violet-950 dark:text-violet-400 dark:ring-violet-700/50",
  },
  zinc: {
    text:  "text-zinc-600 dark:text-zinc-400",
    badge: "bg-zinc-100 text-zinc-700 ring-1 ring-zinc-300 dark:bg-zinc-900 dark:text-zinc-400 dark:ring-zinc-700/50",
  },
};

function ClaimRow({
  c,
  authenticated,
  hasCharacter,
  characterMessage,
  buyingSiteKey,
  onBuyDeed,
}: {
  c: ClaimsMarketClaim;
  authenticated: boolean;
  hasCharacter: boolean;
  characterMessage: string | null;
  buyingSiteKey: string | null;
  onBuyDeed: (siteKey: string) => void;
}) {
  const volT = TIER_CLASSES[c.volumeTierCls] ?? TIER_CLASSES.zinc;
  const rarT = TIER_CLASSES[c.resourceRarityTierCls] ?? TIER_CLASSES.zinc;
  const busy = buyingSiteKey === c.siteKey;
  const btnClass =
    "rounded border border-zinc-300 bg-white px-2 py-0.5 font-mono text-[12px] text-zinc-800 hover:bg-zinc-100 disabled:opacity-50 dark:border-cyan-800 dark:bg-cyan-950/50 dark:text-cyan-200 dark:hover:bg-cyan-900/40";

  return (
    <tr className="border-b border-zinc-200 transition-colors hover:bg-zinc-100 dark:border-cyan-900/40 dark:hover:bg-cyan-950/30">
      <td className="py-1.5 pr-3">
        <span className={`font-mono text-sm font-semibold ${volT.text}`}>{c.roomKey}</span>
      </td>
      <td className="py-1.5 pr-3">
        <span className={`rounded px-1.5 py-0.5 font-mono text-[12px] font-medium ${volT.badge}`}>
          {c.volumeTier}
        </span>
      </td>
      <td className="py-1.5 pr-3">
        <span className={`rounded px-1.5 py-0.5 font-mono text-[12px] font-medium ${rarT.badge}`}>
          {c.resourceRarityTier}
        </span>
      </td>
      <td className="py-1.5 pr-3 font-mono text-sm text-zinc-600 dark:text-zinc-500">{c.hazardLabel}</td>
      <td className="py-1.5 pr-3 text-right font-mono text-sm text-zinc-500 dark:text-zinc-400">
        {c.baseOutputTons.toFixed(1)} t
      </td>
      <td className="py-1.5 pr-3 font-mono text-[12px] text-zinc-600 dark:text-zinc-500">{c.resources}</td>
      <td className="py-1.5 pr-3 font-mono text-[11px] text-zinc-500 dark:text-zinc-400">
        {c.playerListing && c.sellerKey ? c.sellerKey : "—"}
      </td>
      <td className="py-1.5 pl-3">
        {!authenticated ? (
          <Link
            href="/"
            className="font-mono text-[12px] text-zinc-500 underline hover:text-zinc-900 dark:text-cyan-400 dark:hover:text-cyan-300"
          >
            Sign in to claim
          </Link>
        ) : !hasCharacter ? (
          <span className="font-mono text-[11px] leading-snug text-zinc-500 dark:text-zinc-400">
            {characterMessage ?? "Link one playable character to this account for purchases."}
          </span>
        ) : (
          <button
            type="button"
            className={btnClass}
            disabled={buyingSiteKey !== null}
            onClick={() => onBuyDeed(c.siteKey)}
          >
            {busy ? "Buying…" : `Buy deed (${c.listingPriceCr.toLocaleString()} cr)`}
          </button>
        )}
      </td>
    </tr>
  );
}

export default function ClaimsMarketPage() {
  const claimsLoader = useCallback(() => getClaimsMarketState(), []);
  const dashLoader = useCallback(() => getDashboardState(), []);
  const { data, error, loading, reload } = useUiResource(claimsLoader);
  const { data: dash, reload: reloadDash } = useUiResource(dashLoader);

  const [buyingSiteKey, setBuyingSiteKey] = useState<string | null>(null);
  const [purchaseError, setPurchaseError] = useState<string | null>(null);
  const [purchaseSuccess, setPurchaseSuccess] = useState<string | null>(null);

  const authenticated = !!dash?.authenticated;
  const hasCharacter = !!dash?.character;
  const characterMessage = dash?.message ?? null;

  const handleBuyDeed = useCallback(
    async (siteKey: string) => {
      setPurchaseError(null);
      setPurchaseSuccess(null);
      setBuyingSiteKey(siteKey);
      try {
        const res = await purchaseClaimDeed({ siteKey });
        setPurchaseSuccess(
          res.message ??
            "Claim deed purchased. Use a mining package from Mining Outfitters and deploy from the home dashboard."
        );
        reload();
        reloadDash();
      } catch (e) {
        setPurchaseError(e instanceof Error ? e.message : "Purchase failed");
      } finally {
        setBuyingSiteKey(null);
      }
    },
    [reload, reloadDash]
  );

  return (
    <main className="main-content">
      <header className="page-header border-b border-zinc-200 py-3 pl-2 dark:border-cyan-900/50">
        <div className="px-2">
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Claims Market</h1>
          <p className="mt-0.5 text-[12px] text-zinc-500 dark:text-zinc-400">
            Unclaimed mining sites. Buy a deed for a listed site, or purchase a package at Mining Outfitters for a
            random claim.
          </p>
        </div>
      </header>

      <section className="mt-4 overflow-hidden rounded border border-zinc-200 bg-zinc-50 px-2 py-4 dark:border-cyan-900/50 dark:bg-zinc-950/80">
        <div className="-mx-2 mb-2 flex items-center justify-between border-b border-zinc-200 bg-zinc-100 px-3 py-2 dark:border-cyan-800/50 dark:bg-cyan-950/40">
          <h2 className="font-mono text-[12px] font-semibold uppercase tracking-widest text-zinc-600 dark:text-cyan-400/90">
            Available Claims — Unclaimed Sites
          </h2>
          <Countdown
            targetIso={data?.nextDiscoveryAt ?? null}
            prefix="Next discovery:"
            className="font-mono text-[11px] text-zinc-500 dark:text-cyan-500/80"
          />
        </div>

        {purchaseSuccess && (
          <p className="mb-2 font-mono text-[12px] text-emerald-700 dark:text-emerald-400">{purchaseSuccess}</p>
        )}
        {purchaseError && (
          <p className="mb-2 font-mono text-[12px] text-red-600 dark:text-red-400">{purchaseError}</p>
        )}

        {error && (
          <p className="py-1.5 font-mono text-sm text-red-600 dark:text-red-400">Market unavailable: {error}</p>
        )}
        {loading && !data && (
          <p className="animate-pulse py-3 font-mono text-sm text-zinc-600 dark:text-zinc-500">Loading…</p>
        )}
        {data && data.claims.length > 0 && (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-zinc-200 dark:border-cyan-800/50">
                <th className="pb-1.5 font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600 text-left pr-3">
                  Location
                </th>
                <th className="pb-1.5 font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600 text-left pr-3">
                  Volume
                </th>
                <th className="pb-1.5 font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600 text-left pr-3">
                  Rarity
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
                <th className="pb-1.5 font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600 text-left pr-3">
                  Seller
                </th>
                <th className="pb-1.5 font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600 text-left pl-3">
                  Action
                </th>
              </tr>
            </thead>
            <tbody>
              {data.claims.map((c) => (
                <ClaimRow
                  key={c.siteKey}
                  c={c}
                  authenticated={authenticated}
                  hasCharacter={hasCharacter}
                  characterMessage={characterMessage}
                  buyingSiteKey={buyingSiteKey}
                  onBuyDeed={handleBuyDeed}
                />
              ))}
            </tbody>
          </table>
        )}
        {data && data.claims.length === 0 && (
          <p className="py-3 font-mono text-sm text-zinc-600 dark:text-zinc-500">No unclaimed sites available.</p>
        )}
      </section>

      <p className="mt-4 px-2 text-[12px] text-zinc-500 dark:text-zinc-400">
        <Link href="/" className="underline dark:text-cyan-400 dark:hover:text-cyan-300">
          Home dashboard
        </Link>
        {" "}
        — Deploy a mining package with your claim to start production.{" "}
        <Link
          href="/shop?room=Aurnom%20Mining%20Outfitters"
          className="underline dark:text-cyan-400 dark:hover:text-cyan-300"
        >
          Mining Outfitters
        </Link>
        {" "}
        sells packages (random new site + claim). Jackpot chance for elite claims.
      </p>
    </main>
  );
}
