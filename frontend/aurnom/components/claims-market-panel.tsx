"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

import { useControlSurface } from "@/components/control-surface-provider";
import { Countdown } from "@/components/countdown";
import {
  getClaimsMarketState,
  purchaseClaimDeed,
  purchaseListedClaim,
  purchaseRandomFaunaClaim,
  purchaseRandomFloraClaim,
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
import { UI_REFRESH_MS } from "@/lib/ui-refresh-policy";
import { useReloadAfterIso } from "@/lib/use-reload-after-iso";
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
  const kind = c.siteKind ?? "mining";
  const kindLabel = kind === "flora" ? "Flora" : kind === "fauna" ? "Fauna" : "Mining";
  return (
    <div className="rounded border border-cyan-900/40 bg-zinc-950/60 px-3 py-2.5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="truncate text-sm font-medium text-foreground">{c.roomKey}</span>
            <span className="shrink-0 rounded bg-zinc-800/90 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-zinc-300">
              {kindLabel}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${volT.badge}`}>
              {c.volumeTier}
            </span>
            <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${rarT.badge}`}>
              {c.resourceRarityTier}
            </span>
            <span className="text-xs text-ui-muted">{c.hazardLabel}</span>
            <span className="text-xs tabular-nums text-ui-muted">{c.baseOutputTons.toFixed(1)}t</span>
          </div>
          <p className="text-xs leading-snug break-words text-ui-muted">{c.resources}</p>
          {c.sellerKey ? (
            <p className="truncate text-xs text-ui-muted" title={c.sellerKey}>
              Seller: {c.sellerKey}
            </p>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <span className="font-mono text-sm font-semibold tabular-nums text-cyber-cyan">
            {c.listingPriceCr.toLocaleString()}{" "}
            <span className="text-xs font-normal text-amber-400">cr</span>
          </span>
          {!authenticated ? (
            <Link href="/" className={`text-center ${panelInlineLinkClass}`}>
              Sign in
            </Link>
          ) : !hasCharacter ? (
            <span className="max-w-[10rem] text-right text-xs leading-snug text-ui-muted">
              {characterMessage ?? "Link a character to buy."}
            </span>
          ) : (
            <button
              type="button"
              className={panelPrimaryButtonClass}
              disabled={buyingKey !== null}
              onClick={() => (isDeed ? onBuyListedDeed(c.claimId!) : onBuySiteDeed(c.siteKey))}
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
  const { data: cs, reload: reloadControlSurface } = useControlSurface();
  const claimsLoader = useCallback(() => getClaimsMarketState(), []);
  const { data, error, loading, reload } = useUiResource(claimsLoader);

  const [buyingKey, setBuyingKey] = useState<string | null>(null);
  const [randomMiningBusy, setRandomMiningBusy] = useState(false);
  const [randomFloraBusy, setRandomFloraBusy] = useState(false);
  const [randomFaunaBusy, setRandomFaunaBusy] = useState(false);
  const [purchaseError, setPurchaseError] = useState<string | null>(null);
  const [purchaseSuccess, setPurchaseSuccess] = useState<string | null>(null);

  const authenticated = !!cs?.authenticated;
  const hasCharacter = !!cs?.character;
  const characterMessage = cs?.message ?? null;
  const surveyRows = useMemo(() => {
    const m = data?.mineClaims ?? [];
    const f = data?.floraClaims ?? [];
    const a = data?.faunaClaims ?? [];
    return [...m, ...f, ...a];
  }, [data?.mineClaims, data?.floraClaims, data?.faunaClaims]);

  const earliestDiscoveryIso = useMemo(() => {
    const raw = [
      data?.nextDiscoveryAt,
      data?.nextDiscoveryByKind?.mining,
      data?.nextDiscoveryByKind?.flora,
      data?.nextDiscoveryByKind?.fauna,
    ].filter((x): x is string => typeof x === "string" && x.length > 0);
    if (raw.length === 0) return null;
    raw.sort();
    return raw[0];
  }, [data?.nextDiscoveryAt, data?.nextDiscoveryByKind]);

  useReloadAfterIso(earliestDiscoveryIso, reload, UI_REFRESH_MS.postDeadlinePoll);

  const handleBuySiteDeed = useCallback(
    async (siteKey: string) => {
      setPurchaseError(null);
      setPurchaseSuccess(null);
      setBuyingKey(`site:${siteKey}`);
      try {
        const res = await purchaseClaimDeed({ siteKey });
        setPurchaseSuccess(
          res.message ??
            "Claim deed purchased. Use the matching package type and deploy from the home dashboard.",
        );
        reload();
        reloadControlSurface();
      } catch (e) {
        setPurchaseError(e instanceof Error ? e.message : "Purchase failed");
      } finally {
        setBuyingKey(null);
      }
    },
    [reload, reloadControlSurface],
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
        reloadControlSurface();
      } catch (e) {
        setPurchaseError(e instanceof Error ? e.message : "Purchase failed");
      } finally {
        setBuyingKey(null);
      }
    },
    [reload, reloadControlSurface],
  );

  const handlePurchaseRandomMiningClaim = useCallback(async () => {
    setPurchaseError(null);
    setPurchaseSuccess(null);
    setRandomMiningBusy(true);
    try {
      const res = await purchaseRandomMiningClaim();
      setPurchaseSuccess(res.message ?? "Random mining claim purchased.");
      reload();
      reloadControlSurface();
    } catch (e) {
      setPurchaseError(e instanceof Error ? e.message : "Purchase failed");
    } finally {
      setRandomMiningBusy(false);
    }
  }, [reload, reloadControlSurface]);

  const handlePurchaseRandomFloraClaim = useCallback(async () => {
    setPurchaseError(null);
    setPurchaseSuccess(null);
    setRandomFloraBusy(true);
    try {
      const res = await purchaseRandomFloraClaim();
      setPurchaseSuccess(res.message ?? "Random flora claim purchased.");
      reload();
      reloadControlSurface();
    } catch (e) {
      setPurchaseError(e instanceof Error ? e.message : "Purchase failed");
    } finally {
      setRandomFloraBusy(false);
    }
  }, [reload, reloadControlSurface]);

  const handlePurchaseRandomFaunaClaim = useCallback(async () => {
    setPurchaseError(null);
    setPurchaseSuccess(null);
    setRandomFaunaBusy(true);
    try {
      const res = await purchaseRandomFaunaClaim();
      setPurchaseSuccess(res.message ?? "Random fauna claim purchased.");
      reload();
      reloadControlSurface();
    } catch (e) {
      setPurchaseError(e instanceof Error ? e.message : "Purchase failed");
    } finally {
      setRandomFaunaBusy(false);
    }
  }, [reload, reloadControlSurface]);

  const randomQuote = data?.randomMiningClaim ?? null;
  const randomFloraQuote = data?.randomFloraClaim ?? null;
  const randomFaunaQuote = data?.randomFaunaClaim ?? null;

  return (
    <div className="min-w-0">
      <div className={exchangePanelToolbarClass}>
        <h2 className={exchangePanelToolbarTitleClass}>Unclaimed sites</h2>
        <Countdown
          targetIso={earliestDiscoveryIso}
          prefix="Next discovery:"
          className={exchangePanelCountdownClass}
          onExpired={reload}
        />
      </div>

      {purchaseSuccess && <p className="mb-2 text-xs text-emerald-400">{purchaseSuccess}</p>}
      {purchaseError && <p className="mb-2 text-xs text-red-400">{purchaseError}</p>}

      {error && <p className="py-1.5 text-sm text-red-400">Market unavailable: {error}</p>}
      {loading && !data && <p className="animate-pulse text-sm text-ui-muted">Loading…</p>}
      {data && data.claims.length > 0 && (
        <div className="space-y-2">
          {data.claims.map((c) => (
            <ClaimCard
              key={
                c.listingKind === "deed" && c.claimId != null ? `deed-${c.claimId}` : c.siteKey
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

      <div className="mt-4 border-t border-cyan-900/40 pt-3">
        <h3 className={exchangePanelToolbarTitleClass}>Survey: listable sites</h3>
        <p className="mb-2 text-xs leading-snug text-ui-muted">
          Mining, flora, and fauna sites the registry can list as deeds. Shown when signed in (mining
          subset also via <span className="font-mono">GET /ui/mine/claims</span>).
        </p>
        {!authenticated ? (
          <p className="text-xs text-ui-muted">
            <Link href="/" className={panelInlineLinkClass}>
              Sign in
            </Link>{" "}
            to see the listable sites survey.
          </p>
        ) : loading && !data ? (
          <p className="text-xs text-ui-muted">Loading survey…</p>
        ) : surveyRows && surveyRows.length > 0 ? (
          <ul className="max-h-40 space-y-1 overflow-y-auto text-xs">
            {surveyRows.map((row) => {
              const volT = volumeTierStyle(row.volumeTierCls);
              const rarT = rarityTierStyle(row.resourceRarityTierCls);
              return (
                <li
                  key={`${row.siteKind ?? "mining"}-${row.siteKey}`}
                  className="rounded border border-zinc-800/80 bg-zinc-950/40 px-2 py-1.5 font-mono"
                >
                  <div className="flex flex-wrap items-center gap-1">
                    <span className="min-w-0 flex-1 truncate text-foreground">{row.roomKey}</span>
                    {row.siteKind ? (
                      <span className="shrink-0 text-[9px] font-semibold uppercase text-zinc-500">
                        {row.siteKind}
                      </span>
                    ) : null}
                    <span className={`rounded px-1 py-0.5 text-[10px] font-semibold ${volT.badge}`}>
                      {row.volumeTier}
                    </span>
                    <span className={`rounded px-1 py-0.5 text-[10px] font-semibold ${rarT.badge}`}>
                      {row.resourceRarityTier}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[10px] text-ui-muted">{row.resources}</p>
                </li>
              );
            })}
          </ul>
        ) : data ? (
          <p className="text-xs text-ui-muted">No listable sites in the survey.</p>
        ) : null}
      </div>

      <div className="mt-3 space-y-2 border-t border-cyan-900/40 pt-3">
        <p className="text-xs leading-snug text-ui-muted">
          Survey services register a new unclaimed site and issue a deed (mining, flora, or fauna).
          Use <span className="font-mono">deploymine</span>, <span className="font-mono">deployflora</span>
          , or <span className="font-mono">deployfauna</span> on the home dashboard with the matching
          package from{" "}
          <Link href="/shop?room=Aurnom%20Mining%20Outfitters" className={panelInlineLinkClass}>
            Mining Outfitters
          </Link>
          . Small chance for an elite (jackpot) claim.
        </p>
        {!authenticated ? (
          <p className="text-xs text-ui-muted">
            <Link href="/" className={panelInlineLinkClass}>
              Sign in
            </Link>{" "}
            to purchase a random claim.
          </p>
        ) : !hasCharacter ? (
          <p className="text-xs text-ui-muted">{characterMessage ?? "Link a character to purchase."}</p>
        ) : (
          <div className="flex flex-col flex-wrap gap-1.5 sm:flex-row">
            {randomQuote ? (
              <button
                type="button"
                className={`${panelPrimaryButtonClass} max-w-full whitespace-normal text-left leading-snug`}
                disabled={
                  buyingKey !== null || randomMiningBusy || randomFloraBusy || randomFaunaBusy
                }
                onClick={() => void handlePurchaseRandomMiningClaim()}
              >
                {randomMiningBusy ? "…" : `Random mining — ${randomQuote.priceCr.toLocaleString()} cr`}
              </button>
            ) : null}
            {randomFloraQuote ? (
              <button
                type="button"
                className={`${panelPrimaryButtonClass} max-w-full whitespace-normal text-left leading-snug`}
                disabled={
                  buyingKey !== null || randomMiningBusy || randomFloraBusy || randomFaunaBusy
                }
                onClick={() => void handlePurchaseRandomFloraClaim()}
              >
                {randomFloraBusy ? "…" : `Random flora — ${randomFloraQuote.priceCr.toLocaleString()} cr`}
              </button>
            ) : null}
            {randomFaunaQuote ? (
              <button
                type="button"
                className={`${panelPrimaryButtonClass} max-w-full whitespace-normal text-left leading-snug`}
                disabled={
                  buyingKey !== null || randomMiningBusy || randomFloraBusy || randomFaunaBusy
                }
                onClick={() => void handlePurchaseRandomFaunaClaim()}
              >
                {randomFaunaBusy ? "…" : `Random fauna — ${randomFaunaQuote.priceCr.toLocaleString()} cr`}
              </button>
            ) : null}
            {!randomQuote && !randomFloraQuote && !randomFaunaQuote ? (
              <p className="text-xs text-ui-muted">Random claim deeds are not available.</p>
            ) : null}
          </div>
        )}
      </div>

      <p className={exchangePanelFooterClass}>
        <Link href="/" className={panelInlineLinkClass}>
          Home dashboard
        </Link>{" "}
        — Deploy a matching package with your claim to start production. Packages and gear are sold at{" "}
        <Link href="/shop?room=Aurnom%20Mining%20Outfitters" className={panelInlineLinkClass}>
          Mining Outfitters
        </Link>
        .
      </p>
    </div>
  );
}
