"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Countdown } from "@/components/countdown";
import {
  getClaimsMarketState,
  getDashboardState,
  purchaseClaimDeed,
  purchaseListedClaim,
} from "@/lib/ui-api";
import type { ClaimsMarketClaim } from "@/lib/ui-api";
import {
  exchangePanelCountdownClass,
  exchangePanelEmptyClass,
  exchangePanelFooterClass,
  exchangePanelOuterClass,
  exchangePanelToolbarClass,
  exchangePanelToolbarTitleClass,
} from "@/lib/exchange-panel-classes";
import { volumeTierStyle, rarityTierStyle } from "@/lib/mine-tier-styles";
import { useUiResource } from "@/lib/use-ui-resource";

function rowBusyKey(c: ClaimsMarketClaim): string {
  if (c.listingKind === "deed" && c.claimId != null) {
    return `deed:${c.claimId}`;
  }
  return `site:${c.siteKey}`;
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
  const buyBtnClass =
    "rounded bg-cyan-600 px-3 py-1 text-xs font-semibold text-white hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-cyan-700 dark:hover:bg-cyan-600";

  return (
    <div className="rounded border border-zinc-200 px-3 py-2.5 dark:border-cyan-900/40">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
            {c.roomKey}
          </span>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${volT.badge}`}>
              {c.volumeTier}
            </span>
            <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${rarT.badge}`}>
              {c.resourceRarityTier}
            </span>
            <span className="text-[11px] text-zinc-500 dark:text-zinc-400">{c.hazardLabel}</span>
            <span className="text-[11px] tabular-nums text-zinc-400 dark:text-cyan-500/60">
              {c.baseOutputTons.toFixed(1)} t
            </span>
          </div>
          <p className="text-[11px] leading-snug break-words text-zinc-500 dark:text-zinc-400">
            {c.resources}
          </p>
          {c.sellerKey ? (
            <p
              className="truncate text-[11px] text-zinc-400 dark:text-cyan-500/50"
              title={c.sellerKey}
            >
              Seller: {c.sellerKey}
            </p>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <span className="font-mono text-sm font-semibold tabular-nums text-zinc-700 dark:text-cyan-300">
            {c.listingPriceCr.toLocaleString()}{" "}
            <span className="text-[11px] font-normal text-amber-700 dark:text-amber-400">cr</span>
          </span>
          {!authenticated ? (
            <Link
              href="/"
              className="text-center text-xs text-zinc-500 underline hover:text-zinc-900 dark:text-cyan-400 dark:hover:text-cyan-300"
            >
              Sign in
            </Link>
          ) : !hasCharacter ? (
            <span className="max-w-[10rem] text-right text-[10px] leading-snug text-zinc-500 dark:text-zinc-400">
              {characterMessage ?? "Link a character to buy."}
            </span>
          ) : (
            <button
              type="button"
              className={buyBtnClass}
              disabled={buyingKey !== null}
              onClick={() =>
                isDeed ? onBuyListedDeed(c.claimId!) : onBuySiteDeed(c.siteKey)
              }
            >
              {busy ? "…" : "Buy Deed"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function ClaimsMarketPanel() {
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
    <section className={exchangePanelOuterClass}>
      <div className={exchangePanelToolbarClass}>
        <h2 className={exchangePanelToolbarTitleClass}>
          Available Claims — Unclaimed Sites
        </h2>
        <Countdown
          targetIso={data?.nextDiscoveryAt ?? null}
          prefix="Next discovery:"
          className={exchangePanelCountdownClass}
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
        <p className={`animate-pulse ${exchangePanelEmptyClass}`}>Loading…</p>
      )}
      {data && data.claims.length > 0 && (
        <div className="space-y-2">
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
      )}
      {data && data.claims.length === 0 && (
        <p className={exchangePanelEmptyClass}>No unclaimed sites available.</p>
      )}

      <p className={exchangePanelFooterClass}>
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
    </section>
  );
}
