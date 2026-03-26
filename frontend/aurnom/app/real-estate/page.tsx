"use client";

import { useCallback, useEffect, useState } from "react";

import { ClaimsMarketPanel } from "@/components/claims-market-panel";
import { CsButtonLink, CsColumns, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { Countdown } from "@/components/countdown";
import { StoryPanel } from "@/components/story-panel";
import {
  getRealEstateState,
  purchasePropertyDeed,
  purchaseRandomPropertyDeed,
} from "@/lib/ui-api";
import type { PropertyLotRow, PropertyZone } from "@/lib/ui-api";
import {
  exchangePanelCountdownClass,
  exchangePanelEmptyClass,
  exchangePanelOuterClass,
  exchangePanelToolbarClass,
  exchangePanelToolbarTitleClass,
} from "@/lib/exchange-panel-classes";
import { useUiResource } from "@/lib/use-ui-resource";

const REALTY_OFFICE_ROOM = "NanoMegaPlex Real Estate Office";

const TIER_COLOR: Record<number, string> = {
  1: "text-zinc-600 dark:text-cyan-500/80",
  2: "text-sky-700 dark:text-sky-400",
  3: "text-amber-700 dark:text-amber-400",
};

const ZONE_BADGE: Record<string, string> = {
  commercial:  "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
  industrial:  "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  residential: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
};

const RANDOM_ZONE_BTN: Record<PropertyZone, string> = {
  commercial:
    "bg-violet-700 hover:bg-violet-600 dark:bg-violet-800 dark:hover:bg-violet-700",
  residential:
    "bg-emerald-700 hover:bg-emerald-600 dark:bg-emerald-800 dark:hover:bg-emerald-700",
  industrial:
    "bg-amber-700 hover:bg-amber-600 dark:bg-amber-800 dark:hover:bg-amber-700",
};

function ZoneBadge({ zone, label }: { zone: string; label: string }) {
  const cls = ZONE_BADGE[zone] ?? "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400";
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cls}`}>
      {label}
    </span>
  );
}

function LotCard({
  lot,
  onBuy,
  buying,
}: {
  lot: PropertyLotRow;
  onBuy: (lotKey: string) => void;
  buying: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded border border-zinc-200 px-3 py-2.5 dark:border-cyan-900/40">
      <div className="flex min-w-0 flex-col gap-1">
        <span className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
          {lot.lotKey}
        </span>
        <div className="flex flex-wrap items-center gap-1.5">
          <ZoneBadge zone={lot.zone} label={lot.zoneLabel} />
          <span className={`text-[11px] font-semibold ${TIER_COLOR[lot.tier] ?? TIER_COLOR[1]}`}>
            Tier {lot.tier} — {lot.tierLabel}
          </span>
          <span className="text-[11px] text-zinc-400 dark:text-cyan-500/60">
            {lot.sizeUnits} unit{lot.sizeUnits !== 1 ? "s" : ""}
          </span>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2.5">
        <span className="font-mono text-sm font-semibold tabular-nums text-zinc-700 dark:text-cyan-300">
          {lot.listingPriceCr.toLocaleString()}{" "}
          <span className="text-[11px] font-normal text-amber-700 dark:text-amber-400">cr</span>
        </span>
        {lot.purchasable && (
          <button
            type="button"
            disabled={buying}
            onClick={() => onBuy(lot.lotKey)}
            className="rounded bg-cyan-600 px-3 py-1 text-xs font-semibold text-white hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-cyan-700 dark:hover:bg-cyan-600"
          >
            {buying ? "…" : "Buy Deed"}
          </button>
        )}
      </div>
    </div>
  );
}

export default function RealEstatePage() {
  const loader = useCallback(() => getRealEstateState(), []);
  const { data, error, loading, reload } = useUiResource(loader);
  const [buyingLot, setBuyingLot]       = useState<string | null>(null);
  const [randomZoneBusy, setRandomZoneBusy] = useState<PropertyZone | null>(null);
  const [feedback, setFeedback]         = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    const iso = data?.nextPropertyDiscoveryAt;
    if (!iso) return;
    const t = new Date(iso).getTime();
    if (t > Date.now()) return;
    const id = setInterval(() => reload(), 15000);
    return () => clearInterval(id);
  }, [data?.nextPropertyDiscoveryAt, reload]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.location.hash !== "#claims-market") return;
    const el = document.getElementById("claims-market");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [loading, data]);

  async function handleBuy(lotKey: string) {
    setBuyingLot(lotKey);
    setFeedback(null);
    try {
      const res = await purchasePropertyDeed({ lotKey });
      setFeedback({ ok: res.ok, message: res.message ?? (res.ok ? "Purchase complete." : "Purchase failed.") });
      if (res.ok) reload();
    } catch (err) {
      setFeedback({ ok: false, message: err instanceof Error ? err.message : "Purchase failed." });
    } finally {
      setBuyingLot(null);
    }
  }

  async function handleRandomProperty(zone: PropertyZone) {
    setRandomZoneBusy(zone);
    setFeedback(null);
    try {
      const res = await purchaseRandomPropertyDeed({ zone });
      setFeedback({
        ok: res.ok,
        message: res.message ?? (res.ok ? "Purchase complete." : "Purchase failed."),
      });
      if (res.ok) reload();
    } catch (err) {
      setFeedback({ ok: false, message: err instanceof Error ? err.message : "Purchase failed." });
    } finally {
      setRandomZoneBusy(null);
    }
  }

  if (loading) {
    return (
      <main className="main-content">
        <p className="text-sm text-zinc-500 dark:text-cyan-500/80">Loading real estate office…</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="main-content">
        <p className="text-sm text-red-600 dark:text-red-400">
          Failed to load real estate office: {error ?? "Unknown error"}
        </p>
      </main>
    );
  }

  return (
    <CsPage>
      <CsHeader
        title={data.brokerName}
        subtitle={REALTY_OFFICE_ROOM}
        actions={<CsButtonLink href={`/play?room=${encodeURIComponent(REALTY_OFFICE_ROOM)}`}>Back to Play</CsButtonLink>}
      />
      <CsColumns
        left={
          <>
            <CsPanel title="Real Estate Office">
              <StoryPanel title="Real Estate Office" lines={data.storyLines} />
              {feedback && (
                <p
                  className={`mt-1 rounded px-3 py-2 text-sm ${
                    feedback.ok
                      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400"
                      : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                  }`}
                >
                  {feedback.message}
                </p>
              )}
            </CsPanel>
            <CsPanel title="Property Market">
              <div className={exchangePanelOuterClass}>
                <div className={exchangePanelToolbarClass}>
                  <h2 id="property-listings-heading" className={exchangePanelToolbarTitleClass}>
                    Property market — listable parcels
                  </h2>
                  <Countdown
                    targetIso={data.nextPropertyDiscoveryAt ?? null}
                    prefix="Next restock:"
                    className={exchangePanelCountdownClass}
                    onExpired={reload}
                  />
                </div>

                {data.lots.length === 0 ? (
                  <p className={exchangePanelEmptyClass}>No lots currently available.</p>
                ) : (
                  <div className="mt-2 flex flex-col gap-2">
                    {data.lots.map((lot) => (
                      <LotCard
                        key={lot.lotKey}
                        lot={lot}
                        onBuy={handleBuy}
                        buying={buyingLot === lot.lotKey}
                      />
                    ))}
                  </div>
                )}

                <div className="mt-3 space-y-2 border-t border-zinc-200 pt-3 dark:border-cyan-900/40">
                  <p className="text-[11px] leading-snug text-zinc-600 dark:text-cyan-500/75">
                    Buy a random listable parcel by zone (price follows tier and zone, same as choosing a
                    specific lot).
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {(
                      [
                        { zone: "commercial" as const, label: "Buy random commercial" },
                        { zone: "residential" as const, label: "Buy random residential" },
                        { zone: "industrial" as const, label: "Buy random industrial" },
                      ] as const
                    ).map(({ zone, label }) => (
                      <button
                        key={zone}
                        type="button"
                        disabled={randomZoneBusy !== null || buyingLot !== null}
                        onClick={() => void handleRandomProperty(zone)}
                        className={`rounded px-3 py-1.5 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 ${RANDOM_ZONE_BTN[zone]}`}
                      >
                        {randomZoneBusy === zone ? "…" : label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </CsPanel>
          </>
        }
        right={
          <section id="claims-market" aria-label="Claims market" className="scroll-mt-4 min-w-0">
            <CsPanel title="Claims Market">
              <ClaimsMarketPanel />
            </CsPanel>
          </section>
        }
      />
    </CsPage>
  );
}
