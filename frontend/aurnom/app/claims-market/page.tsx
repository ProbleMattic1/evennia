"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  getClaimsMarketState,
  getDashboardState,
  purchaseClaimDeed,
  purchaseListedClaim,
} from "@/lib/ui-api";
import type { ClaimsMarketClaim } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";
import { volumeTierStyle, rarityTierStyle } from "@/lib/mine-tier-styles";
import { Countdown } from "@/components/countdown";

function rowBusyKey(c: ClaimsMarketClaim): string {
  if (c.listingKind === "deed" && c.claimId != null) {
    return `deed:${c.claimId}`;
  }
  return `site:${c.siteKey}`;
}

function ClaimRow({
  c,
  authenticated,
  hasCharacter,
  characterMessage,
  buyingKey,
  onBuySiteDeed,
  onBuyListedDeed,
}: {
  c: ClaimsMarketClaim;
  authenticated: boolean;
  hasCharacter: boolean;
  characterMessage: string | null;
  buyingKey: string | null;
  onBuySiteDeed: (siteKey: string) => void;
  onBuyListedDeed: (claimId: number) => void;
}) {
  const volT = volumeTierStyle(c.volumeTierCls);
  const rarT = rarityTierStyle(c.resourceRarityTierCls);
  const busyKey = rowBusyKey(c);
  const busy = buyingKey === busyKey;
  const isDeed = c.listingKind === "deed" && c.claimId != null;
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
        {c.sellerKey ?? "—"}
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
            disabled={buyingKey !== null}
            onClick={() =>
              isDeed ? onBuyListedDeed(c.claimId!) : onBuySiteDeed(c.siteKey)
            }
          >
            {busy ? "Buying…" : `Buy deed (${c.listingPriceCr.toLocaleString()} cr)`}
          </button>
        )}
      </td>
    </tr>
  );
}

function ClaimCard({
  c,
  authenticated,
  hasCharacter,
  characterMessage,
  buyingKey,
  onBuySiteDeed,
  onBuyListedDeed,
}: {
  c: ClaimsMarketClaim;
  authenticated: boolean;
  hasCharacter: boolean;
  characterMessage: string | null;
  buyingKey: string | null;
  onBuySiteDeed: (siteKey: string) => void;
  onBuyListedDeed: (claimId: number) => void;
}) {
  const volT = volumeTierStyle(c.volumeTierCls);
  const rarT = rarityTierStyle(c.resourceRarityTierCls);
  const busyKey = rowBusyKey(c);
  const busy = buyingKey === busyKey;
  const isDeed = c.listingKind === "deed" && c.claimId != null;
  const btnClass =
    "w-full rounded border border-zinc-300 bg-white px-3 py-2 font-mono text-[12px] text-zinc-800 hover:bg-zinc-100 disabled:opacity-50 dark:border-cyan-800 dark:bg-cyan-950/50 dark:text-cyan-200 dark:hover:bg-cyan-900/40";

  return (
    <article className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-cyan-900/50 dark:bg-zinc-950/80">
      <p className={`font-mono text-sm font-semibold ${volT.text}`}>{c.roomKey}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <span className={`rounded px-1.5 py-0.5 font-mono text-[12px] font-medium ${volT.badge}`}>
          {c.volumeTier}
        </span>
        <span className={`rounded px-1.5 py-0.5 font-mono text-[12px] font-medium ${rarT.badge}`}>
          {c.resourceRarityTier}
        </span>
      </div>
      <dl className="mt-2 space-y-1 font-mono text-[12px] text-zinc-600 dark:text-zinc-400">
        <div className="flex justify-between gap-2">
          <dt className="text-zinc-500 dark:text-zinc-500">Hazard</dt>
          <dd>{c.hazardLabel}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-zinc-500 dark:text-zinc-500">Base output</dt>
          <dd className="tabular-nums">{c.baseOutputTons.toFixed(1)} t</dd>
        </div>
        <div>
          <dt className="text-zinc-500 dark:text-zinc-500">Resources</dt>
          <dd className="mt-0.5 break-words">{c.resources}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-zinc-500 dark:text-zinc-500">Seller</dt>
          <dd
            className="min-w-0 truncate text-right text-[11px]"
            title={c.sellerKey ?? undefined}
          >
            {c.sellerKey ?? "—"}
          </dd>
        </div>
      </dl>
      <div className="mt-3">
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
            disabled={buyingKey !== null}
            onClick={() =>
              isDeed ? onBuyListedDeed(c.claimId!) : onBuySiteDeed(c.siteKey)
            }
          >
            {busy ? "Buying…" : `Buy deed (${c.listingPriceCr.toLocaleString()} cr)`}
          </button>
        )}
      </div>
    </article>
  );
}

export default function ClaimsMarketPage() {
  const claimsLoader = useCallback(() => getClaimsMarketState(), []);
  const dashLoader = useCallback(() => getDashboardState(), []);
  const { data, error, loading, reload } = useUiResource(claimsLoader);
  const { data: dash, reload: reloadDash } = useUiResource(dashLoader);

  const [buyingKey, setBuyingKey] = useState<string | null>(null);
  const [purchaseError, setPurchaseError] = useState<string | null>(null);
  const [purchaseSuccess, setPurchaseSuccess] = useState<string | null>(null);

  const authenticated = !!dash?.authenticated;
  const hasCharacter = !!dash?.character;
  const characterMessage = dash?.message ?? null;

  useEffect(() => {
    const iso = data?.nextDiscoveryAt;
    if (!iso) return;
    const t = new Date(iso).getTime();
    if (t > Date.now()) return;
    const id = setInterval(() => reload(), 15000);
    return () => clearInterval(id);
  }, [data?.nextDiscoveryAt, reload]);

  const handleBuySiteDeed = useCallback(
    async (siteKey: string) => {
      setPurchaseError(null);
      setPurchaseSuccess(null);
      setBuyingKey(`site:${siteKey}`);
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
        setBuyingKey(null);
      }
    },
    [reload, reloadDash]
  );

  const handleBuyListedDeed = useCallback(
    async (claimId: number) => {
      setPurchaseError(null);
      setPurchaseSuccess(null);
      setBuyingKey(`deed:${claimId}`);
      try {
        const res = await purchaseListedClaim({ claimId });
        setPurchaseSuccess(res.message ?? "Claim deed purchased.");
        reload();
        reloadDash();
      } catch (e) {
        setPurchaseError(e instanceof Error ? e.message : "Purchase failed");
      } finally {
        setBuyingKey(null);
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
            Unclaimed mining sites and player-listed deeds. Buy a deed, or list one from your claim page.
          </p>
        </div>
      </header>

      <section className="mt-4 overflow-x-auto rounded border border-zinc-200 bg-zinc-50 px-2 py-4 dark:border-cyan-900/50 dark:bg-zinc-950/80">
        <div className="-mx-2 mb-2 flex flex-col gap-2 border-b border-zinc-200 bg-zinc-100 px-3 py-2 sm:flex-row sm:items-center sm:justify-between dark:border-cyan-800/50 dark:bg-cyan-950/40">
          <h2 className="min-w-0 font-mono text-[12px] font-semibold uppercase tracking-widest text-zinc-600 dark:text-cyan-400/90">
            Available Claims — Unclaimed Sites
          </h2>
          <Countdown
            targetIso={data?.nextDiscoveryAt ?? null}
            prefix="Next discovery:"
            className="shrink-0 font-mono text-[11px] text-zinc-500 dark:text-cyan-500/80"
            onExpired={reload}
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
          <>
            <div className="space-y-3 md:hidden">
              {data.claims.map((c) => (
                <ClaimCard
                  key={
                    c.listingKind === "deed" && c.claimId != null
                      ? `deed-${c.claimId}`
                      : c.siteKey
                  }
                  c={c}
                  authenticated={authenticated}
                  hasCharacter={hasCharacter}
                  characterMessage={characterMessage}
                  buyingKey={buyingKey}
                  onBuySiteDeed={handleBuySiteDeed}
                  onBuyListedDeed={handleBuyListedDeed}
                />
              ))}
            </div>
            <div className="-mx-2 hidden overflow-x-auto px-2 md:block">
              <table className="w-full min-w-[56rem] text-left">
                <thead>
                  <tr className="border-b border-zinc-200 dark:border-cyan-800/50">
                    <th className="pb-1.5 pr-3 text-left font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600">
                      Location
                    </th>
                    <th className="pb-1.5 pr-3 text-left font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600">
                      Volume
                    </th>
                    <th className="pb-1.5 pr-3 text-left font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600">
                      Rarity
                    </th>
                    <th className="pb-1.5 pr-3 text-left font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600">
                      Hazard
                    </th>
                    <th className="pb-1.5 pr-3 text-right font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600">
                      Base t
                    </th>
                    <th className="pb-1.5 pr-3 text-left font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600">
                      Resources
                    </th>
                    <th className="pb-1.5 pr-3 text-left font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600">
                      Seller
                    </th>
                    <th className="pb-1.5 pl-3 text-left font-mono text-[12px] uppercase tracking-wider text-zinc-500 dark:text-zinc-600">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.claims.map((c) => (
                    <ClaimRow
                      key={
                        c.listingKind === "deed" && c.claimId != null
                          ? `deed-${c.claimId}`
                          : c.siteKey
                      }
                      c={c}
                      authenticated={authenticated}
                      hasCharacter={hasCharacter}
                      characterMessage={characterMessage}
                      buyingKey={buyingKey}
                      onBuySiteDeed={handleBuySiteDeed}
                      onBuyListedDeed={handleBuyListedDeed}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        {data && data.claims.length === 0 && (
          <p className="py-3 font-mono text-sm text-zinc-600 dark:text-zinc-500">No unclaimed sites available.</p>
        )}
      </section>

      <p className="mt-4 px-2 text-[12px] text-zinc-500 dark:text-zinc-400">
        <Link href="/" className="underline dark:text-cyan-400 dark:hover:text-cyan-300">
          Home dashboard
        </Link>{" "}
        — Deploy a mining package with your claim to start production.{" "}
        <Link
          href="/shop?room=Aurnom%20Mining%20Outfitters"
          className="underline dark:text-cyan-400 dark:hover:text-cyan-300"
        >
          Mining Outfitters
        </Link>{" "}
        sells packages (random new site + claim). Jackpot chance for elite claims.
      </p>
    </main>
  );
}
