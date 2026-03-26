"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { ClaimsMarketPanel } from "@/components/claims-market-panel";
import { Countdown } from "@/components/countdown";
import { StoryPanel } from "@/components/story-panel";
import { getRealEstateState, purchasePropertyDeed } from "@/lib/ui-api";
import type { PropertyLotRow } from "@/lib/ui-api";
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
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
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
    <main className="main-content">
      <header className="page-header flex items-center justify-between border-b border-zinc-200 py-3 pl-2 dark:border-cyan-900/50">
        <div className="px-2">
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
            {data.brokerName}
          </h1>
          <p className="mt-0.5 text-[12px] text-zinc-500 dark:text-cyan-500/80">
            {REALTY_OFFICE_ROOM}
          </p>
        </div>
        <Link
          href={`/play?room=${encodeURIComponent(REALTY_OFFICE_ROOM)}`}
          className="rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-800 hover:bg-zinc-100 dark:border-cyan-700/50 dark:text-cyan-400 dark:hover:bg-cyan-950/40 dark:hover:text-cyan-300"
        >
          Back to Play
        </Link>
      </header>

      <div className="flex flex-col gap-2 px-2 py-2">
        <StoryPanel title="Real Estate Office" lines={data.storyLines} />

        {feedback && (
          <p
            className={`rounded px-3 py-2 text-sm ${
              feedback.ok
                ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400"
                : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
            }`}
          >
            {feedback.message}
          </p>
        )}

        <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
          <section aria-labelledby="property-listings-heading" className="min-w-0 px-2 py-2">
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
            </div>
          </section>

          <section
            id="claims-market"
            aria-label="Claims market"
            className="scroll-mt-4 min-w-0 px-2 py-2"
          >
            <ClaimsMarketPanel />
          </section>
        </div>
      </div>
    </main>
  );
}
