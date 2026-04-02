"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { ClaimsMarketPanel } from "@/components/claims-market-panel";
import { PropertyDeedResaleBrowse } from "@/components/property-deed-resale-browse";
import { CsButtonLink, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { Countdown } from "@/components/countdown";
import { VenueBillboardStoryFrame } from "@/components/venue-billboard-story-frame";
import {
  EMPTY_ROOM_AMBIENT,
  getRealEstateState,
  purchasePropertyDeed,
  purchaseRandomPropertyDeed,
} from "@/lib/ui-api";
import type { PropertyLotRow, PropertyZone } from "@/lib/ui-api";
import {
  exchangePanelCountdownClass,
  exchangePanelToolbarClass,
  exchangePanelToolbarTitleClass,
  panelPrimaryButtonClass,
} from "@/lib/exchange-panel-classes";
import { UI_REFRESH_MS } from "@/lib/ui-refresh-policy";
import { useReloadAfterIso } from "@/lib/use-reload-after-iso";
import { useUiResource } from "@/lib/use-ui-resource";

const TIER_COLOR: Record<number, string> = {
  1: "text-ui-accent-readable",
  2: "text-sky-700 dark:text-sky-400",
  3: "text-amber-700 dark:text-amber-400",
};

const ZONE_BADGE: Record<string, string> = {
  commercial:  "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
  industrial:  "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  residential: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
};

function ZoneBadge({ zone, label }: { zone: string; label: string }) {
  const cls = ZONE_BADGE[zone] ?? "bg-zinc-100 text-ui-muted dark:bg-zinc-800 dark:text-ui-muted";
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${cls}`}>
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
    <div className="flex items-center justify-between gap-3 rounded border border-cyan-900/40 bg-zinc-950/60 px-3 py-2.5">
      <div className="flex min-w-0 flex-col gap-1">
        <span className="truncate text-sm font-medium text-zinc-900 dark:text-foreground">
          {lot.lotKey}
        </span>
        <div className="flex flex-wrap items-center gap-1.5">
          <ZoneBadge zone={lot.zone} label={lot.zoneLabel} />
          <span className={`text-xs font-semibold ${TIER_COLOR[lot.tier] ?? TIER_COLOR[1]}`}>
            Tier {lot.tier} — {lot.tierLabel}
          </span>
          <span className="text-xs text-ui-muted">
            {lot.sizeUnits} unit{lot.sizeUnits !== 1 ? "s" : ""}
          </span>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2.5">
        <span className="font-mono text-sm font-semibold tabular-nums text-zinc-700 dark:text-cyber-cyan">
          {lot.listingPriceCr.toLocaleString()}{" "}
          <span className="text-xs font-normal text-amber-700 dark:text-amber-400">cr</span>
        </span>
        {lot.purchasable && (
          <button
            type="button"
            disabled={buying}
            onClick={() => onBuy(lot.lotKey)}
            className={panelPrimaryButtonClass}
          >
            {buying ? "…" : "Buy Deed"}
          </button>
        )}
      </div>
    </div>
  );
}

function RealEstatePageInner() {
  const searchParams = useSearchParams();
  const venue = searchParams.get("venue")?.trim() || undefined;
  const loader = useCallback(() => getRealEstateState(venue), [venue]);
  const { data, error, loading, reload } = useUiResource(loader);
  const [buyingLot, setBuyingLot]       = useState<string | null>(null);
  const [randomZoneBusy, setRandomZoneBusy] = useState<PropertyZone | null>(null);
  const [feedback, setFeedback]         = useState<{ ok: boolean; message: string } | null>(null);

  useReloadAfterIso(data?.nextPropertyDiscoveryAt ?? null, reload, UI_REFRESH_MS.postDeadlinePoll);

  useEffect(() => {
    if (typeof window === "undefined" || loading) return;
    const hash = window.location.hash;
    if (hash === "#claims-market") {
      const el = document.getElementById("claims-market");
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (hash === "#property-deed-resale-market") {
      const el = document.getElementById("property-deed-resale-market");
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
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

  async function handleRandomProperty(zone: PropertyZone) {
    setRandomZoneBusy(zone);
    setFeedback(null);
    try {
      const res = await purchaseRandomPropertyDeed({
        zone,
        venueId: venue ?? data?.venueId,
      });
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
      <CsPage>
        <p className="text-sm text-ui-accent-readable">Loading real estate office…</p>
      </CsPage>
    );
  }

  if (error || !data) {
    return (
      <CsPage>
        <p className="text-sm text-red-600 dark:text-red-400">
          Failed to load real estate office: {error ?? "Unknown error"}
        </p>
      </CsPage>
    );
  }

  return (
    <CsPage>
      <CsHeader
        title={data.brokerName}
        subtitle={data.officeRoomKey ?? "Real Estate office"}
        actions={<CsButtonLink href="/">Back to dashboard</CsButtonLink>}
      />
      <VenueBillboardStoryFrame
        panelTitle="Location & story"
        roomName={data.roomName ?? data.officeRoomKey ?? data.brokerName}
        ambient={data.ambient ?? EMPTY_ROOM_AMBIENT}
        storyLines={data.storyLines}
        storySubheading="Office output"
      />
      <div className="flex min-h-0 min-w-0 flex-col gap-1.5 overflow-y-auto p-1.5 md:min-h-0">
        {feedback ? (
          <CsPanel title="Real Estate Office">
            <p
              className={`rounded border px-2 py-1.5 text-xs ${
                feedback.ok
                  ? "border-emerald-800/50 text-emerald-400"
                  : "border-red-800/50 text-red-400"
              }`}
            >
              {feedback.message}
            </p>
          </CsPanel>
        ) : null}
        <CsPanel title="Property Market">
            <div className={exchangePanelToolbarClass}>
              <h2 id="property-listings-heading" className={exchangePanelToolbarTitleClass}>
                Listable parcels
              </h2>
              <Countdown
                targetIso={data.nextPropertyDiscoveryAt ?? null}
                prefix="Next restock:"
                className={exchangePanelCountdownClass}
                onExpired={reload}
              />
            </div>

            {data.lots.length > 0 ? (
              <div className="mt-1 flex flex-col gap-2">
                {data.lots.map((lot) => (
                  <LotCard
                    key={lot.lotKey}
                    lot={lot}
                    onBuy={handleBuy}
                    buying={buyingLot === lot.lotKey}
                  />
                ))}
              </div>
            ) : null}

            <PropertyDeedResaleBrowse onPurchased={() => void reload()} />

            <div className="mt-3 space-y-2 border-t border-cyan-900/40 pt-2">
              <p className="text-xs leading-snug text-ui-muted">
                Buy a random listable parcel by zone (price follows tier and zone, same as choosing a
                specific lot).
              </p>
              <div className="flex flex-wrap gap-1.5">
                {(
                  [
                    { zone: "commercial" as const, label: "Random commercial" },
                    { zone: "residential" as const, label: "Random residential" },
                    { zone: "industrial" as const, label: "Random industrial" },
                  ] as const
                ).map(({ zone, label }) => (
                  <button
                    key={zone}
                    type="button"
                    disabled={randomZoneBusy !== null || buyingLot !== null}
                    onClick={() => void handleRandomProperty(zone)}
                    className={panelPrimaryButtonClass}
                  >
                    {randomZoneBusy === zone ? "…" : label}
                  </button>
                ))}
              </div>
            </div>
        </CsPanel>
        <section id="claims-market" aria-label="Claims market" className="scroll-mt-4 min-w-0">
          <CsPanel title="Claims Market">
            <ClaimsMarketPanel />
          </CsPanel>
        </section>
      </div>
    </CsPage>
  );
}

export default function RealEstatePage() {
  return (
    <Suspense
      fallback={
        <CsPage>
          <p className="text-sm text-ui-accent-readable">Loading real estate office…</p>
        </CsPage>
      }
    >
      <RealEstatePageInner />
    </Suspense>
  );
}
