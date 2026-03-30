"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Countdown } from "@/components/countdown";
import {
  getClaimsMarketState,
  getDashboardState,
  purchaseClaimDeed,
  purchaseListedClaim,
  purchaseRandomMiningClaim,
} from "@/lib/ui-api";
import type { ClaimsMarketClaim } from "@/lib/ui-api";
import {
  exchangePanelCountdownClass,
  exchangePanelEmptyClass,
  exchangePanelFooterClass,
  exchangePanelToolbarClass,
  exchangePanelToolbarTitleClass,
  panelInlineLinkClass,
  panelPrimaryButtonClass,
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
  return (
    <div className="rounded border border-cyan-900/40 bg-zinc-950/60 px-3 py-2.5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="truncate text-sm font-medium text-zinc-100">
            {c.roomKey}
          </span>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${volT.badge}`}>
              {c.volumeTier}
            </span>
            <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${rarT.badge}`}>
              {c.resourceRarityTier}
            </span>
            <span className="text-[11px] text-ui-muted">{c.hazardLabel}</span>
            <span className="text-[11px] tabular-nums text-ui-muted">
              {c.baseOutputTons.toFixed(1)} t
            </span>
          </div>
          <p className="text-[11px] leading-snug break-words text-ui-muted">
            {c.resources}
          </p>
          {c.sellerKey ? (
            <p className="truncate text-[11px] text-ui-muted" title={c.sellerKey}>
              Seller: {c.sellerKey}
            </p>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <span className="font-mono text-sm font-semibold tabular-nums text-cyan-300">
            {c.listingPriceCr.toLocaleString()}{" "}
            <span className="text-[11px] font-normal text-amber-400">cr</span>
          </span>
          {!authenticated ? (
            <Link href="/" className={`text-center ${panelInlineLinkClass}`}>
              Sign in
            </Link>
          ) : !hasCharacter ? (
            <span className="max-w-[10rem] text-right text-[10px] leading-snug text-ui-muted">
              {characterMessage ?? "Link a character to buy."}
            </span>
          ) : (
            <button
              type="button"
              className={panelPrimaryButtonClass}
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
  const [randomMiningBusy, setRandomMiningBusy] = useState(false);
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
            "Claim deed purchased. Use a mining package and deploy from the home dashboard."
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

  const handlePurchaseRandomMiningClaim = useCallback(async () => {
    setPurchaseError(null);
    setPurchaseSuccess(null);
    setRandomMiningBusy(true);
    try {
      const res = await purchaseRandomMiningClaim();
      setPurchaseSuccess(res.message ?? "Random mining claim purchased.");
      reload();
      reloadDash();
    } catch (e) {
      setPurchaseError(e instanceof Error ? e.message : "Purchase failed");
    } finally {
      setRandomMiningBusy(false);
    }
  }, [reload, reloadDash]);

  const randomQuote = data?.randomMiningClaim ?? null;

  return (
    <div className="min-w-0">
      <div className={exchangePanelToolbarClass}>
        <h2 className={exchangePanelToolbarTitleClass}>Unclaimed sites</h2>
        <Countdown
          targetIso={data?.nextDiscoveryAt ?? null}
          prefix="Next discovery:"
          className={exchangePanelCountdownClass}
          onExpired={reload}
        />
      </div>

      {purchaseSuccess && (
        <p className="mb-2 text-[11px] text-emerald-400">{purchaseSuccess}</p>
      )}
      {purchaseError && <p className="mb-2 text-[11px] text-red-400">{purchaseError}</p>}

      {error && (
        <p className="py-1.5 text-sm text-red-400">Market unavailable: {error}</p>
      )}
      {loading && !data && (
        <p className="animate-pulse text-sm text-ui-muted">Loading…</p>
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

      <div className="mt-3 space-y-2 border-t border-cyan-900/40 pt-3">
        <p className="text-[11px] leading-snug text-ui-muted">
          Survey services register a new unclaimed deposit and issue a deed. You receive one random
          mining claim; use{" "}
          <Link href="/" className={panelInlineLinkClass}>
            deploymine
          </Link>{" "}
          on the home dashboard with a mining package from{" "}
          <Link
            href="/shop?room=Aurnom%20Mining%20Outfitters"
            className={panelInlineLinkClass}
          >
            Mining Outfitters
          </Link>{" "}
          to develop it. Small chance for an elite (jackpot) claim.
        </p>
        {!authenticated ? (
          <p className="text-[11px] text-ui-muted">
            <Link href="/" className={panelInlineLinkClass}>
              Sign in
            </Link>{" "}
            to purchase a random claim.
          </p>
        ) : !hasCharacter ? (
          <p className="text-[11px] text-ui-muted">
            {characterMessage ?? "Link a character to purchase."}
          </p>
        ) : randomQuote ? (
          <div className="flex flex-wrap items-start gap-1.5">
            <button
              type="button"
              className={`${panelPrimaryButtonClass} max-w-full whitespace-normal text-left leading-snug`}
              disabled={buyingKey !== null || randomMiningBusy}
              onClick={() => void handlePurchaseRandomMiningClaim()}
            >
              {randomMiningBusy
                ? "…"
                : `Random mining claim — ${randomQuote.priceCr.toLocaleString()} cr`}
            </button>
          </div>
        ) : (
          <p className="text-[11px] text-ui-muted">
            Random mining claim deed is not available.
          </p>
        )}
      </div>

      <p className={exchangePanelFooterClass}>
        <Link href="/" className={panelInlineLinkClass}>
          Home dashboard
        </Link>{" "}
        — Deploy a mining package with your claim to start production. Mining packages and gear are
        sold at{" "}
        <Link
          href="/shop?room=Aurnom%20Mining%20Outfitters"
          className={panelInlineLinkClass}
        >
          Mining Outfitters
        </Link>
        .
      </p>
    </div>
  );
}
