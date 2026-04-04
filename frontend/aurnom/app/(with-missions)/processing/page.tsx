"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { PanelExpandButton } from "@/components/panel-expand-button";
import { CsButtonLink, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { CommodityTickerTable } from "@/components/commodity-ticker";
import { OreReceivingBayTiles } from "@/components/ore-receiving-bay-tiles";
import { VenueBillboardStoryFrame } from "@/components/venue-billboard-story-frame";
import { useDashboardPanelOpen } from "@/lib/use-dashboard-panel-open";
import { formatCr as cr } from "@/lib/format-units";
import { EMPTY_ROOM_AMBIENT, getProcessingState, playInteract } from "@/lib/ui-api";
import { intervalMs, isUiPollPaused } from "@/lib/ui-refresh-policy";
import { useUiResource } from "@/lib/use-ui-resource";
import {
  WithMissionsProcessingBelowMissionsSlot,
  WithMissionsProcessingTopSlot,
  WithMissionsProcessingWideSlot,
} from "@/lib/with-missions-processing-split";

function ProcurementBoardPanel() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function runList() {
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      await playInteract({
        interactionKey: "contractboard",
        payload: { action: "list" },
      });
      setNotice("Board listing sent to your game log (dashboard).");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Procurement board action failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-1 min-w-0 space-y-1">
      <p className="break-words text-xs text-ui-accent-readable">
        Requires your character to be at the plant in-game. Accept or complete contracts via{" "}
        <code className="break-all font-mono text-xs">play/interact</code> with{" "}
        <code className="break-all font-mono text-xs">contractboard</code> and payload{" "}
        <code className="break-all font-mono text-xs">action: accept | complete</code>,{" "}
        <code className="break-all font-mono text-xs">contractId</code>.
      </p>
      <button
        type="button"
        disabled={busy}
        onClick={() => void runList()}
        className="rounded border border-cyan-700/50 bg-cyan-950/40 px-2 py-1 text-xs text-cyber-cyan hover:bg-cyan-900/50 disabled:opacity-50"
      >
        {busy ? "…" : "List open contracts (game log)"}
      </button>
      {error ? <p className="text-xs text-red-500">{error}</p> : null}
      {notice ? <p className="text-xs text-ui-accent-readable">{notice}</p> : null}
    </div>
  );
}

function ProcessingPageInner() {
  const searchParams = useSearchParams();
  const venue = searchParams.get("venue")?.trim() || undefined;
  const loader = useCallback(() => getProcessingState(venue), [venue]);
  const { data, error, loading, reload } = useUiResource(loader);

  useEffect(() => {
    const ms = intervalMs("controlSurface", null);
    const id = window.setInterval(() => {
      if (!isUiPollPaused()) reload();
    }, ms);
    return () => window.clearInterval(id);
  }, [reload]);

  const [marketSnapshotOpen, setMarketSnapshotOpen] = useDashboardPanelOpen("processing:market-snapshot", true);

  if (loading) {
    return (
      <CsPage>
        <p className="text-sm text-ui-accent-readable">Loading processing plant…</p>
      </CsPage>
    );
  }

  if (error || !data) {
    return (
      <CsPage>
        <p className="text-sm text-red-600 dark:text-red-400">
          Failed to load processing plant: {error ?? "Unknown error"}
        </p>
      </CsPage>
    );
  }

  const FEE = 0.03;
  const oreRows = data.oreReceivingBay ?? [];
  const rollup = oreRows.reduce(
    (acc, r) => {
      const est = typeof r.estimatedValueCr === "number" && !Number.isNaN(r.estimatedValueCr) ? r.estimatedValueCr : 0;
      acc.market += est;
      acc.spent += Math.floor(est * (1 - FEE));
      acc.sell += Math.floor(est * (1 + FEE));
      return acc;
    },
    { spent: 0, market: 0, sell: 0 },
  );
  const net = rollup.sell - rollup.spent;

  return (
    <CsPage>
      <WithMissionsProcessingTopSlot>
        <CsHeader
          title={data.plantName}
          subtitle={data.roomName}
          actions={
            <div className="flex flex-wrap gap-1">
              <CsButtonLink href="/refinery">Refinery</CsButtonLink>
              <CsButtonLink href="/" variant="dashboard">
                Dashboard
              </CsButtonLink>
            </div>
          }
        />
        <VenueBillboardStoryFrame
          panelTitle="Location & story"
          roomName={data.roomName}
          ambient={data.ambient ?? EMPTY_ROOM_AMBIENT}
          storyLines={data.storyLines}
          storySubheading="Plant output"
        />
      </WithMissionsProcessingTopSlot>

      <WithMissionsProcessingBelowMissionsSlot>
        <section className="mb-1 min-w-0">
          <div className="flex min-w-0 flex-wrap items-center gap-x-1 gap-y-0.5 bg-cyan-900/30 px-1.5 py-0.5 text-xs font-bold uppercase tracking-widest text-cyber-cyan">
            <span className="min-w-0 break-words text-cyber-cyan">Market Snapshot</span>
            <div className="ml-auto flex min-w-0 shrink-0 flex-wrap items-center justify-end gap-1 normal-case tracking-normal">
              <span className="min-w-0 max-w-full text-right font-mono text-ui-caption font-normal break-words [overflow-wrap:anywhere] sm:whitespace-nowrap">
                <span className="text-ui-muted">spent </span>
                <span className="text-cyber-cyan/90">{cr(rollup.spent)}</span>
                <span className="text-ui-muted"> · </span>
                <span className="text-ui-muted">mkt </span>
                <span className="text-cyber-cyan/90">{cr(rollup.market)}</span>
                <span className="text-ui-muted"> · </span>
                <span className="text-ui-muted">sell </span>
                <span className="text-cyber-cyan/90">{cr(rollup.sell)}</span>
                <span className="text-ui-muted"> · </span>
                <span className="text-ui-muted">net </span>
                <span className="text-cyber-cyan/90">{cr(net)}</span>
              </span>
              <PanelExpandButton
                open={marketSnapshotOpen}
                onClick={() => setMarketSnapshotOpen((v) => !v)}
                aria-label={`${marketSnapshotOpen ? "Collapse" : "Expand"} Market Snapshot`}
                className="shrink-0"
              />
            </div>
          </div>
          {marketSnapshotOpen ? (
            <div className="border border-cyan-900/40 bg-zinc-950/80 p-1">
              <OreReceivingBayTiles rows={oreRows} />
            </div>
          ) : null}
        </section>
      </WithMissionsProcessingBelowMissionsSlot>

      <WithMissionsProcessingWideSlot>
        <div className="flex flex-col gap-1.5">
          <div className="min-w-0">
            <CsPanel title="Procurement board">
              <ProcurementBoardPanel />
            </CsPanel>
          </div>
        </div>
      </WithMissionsProcessingWideSlot>

      <div className="min-w-0">
        <CsPanel title="Commodity Board">
          <CommodityTickerTable />
        </CsPanel>
      </div>
    </CsPage>
  );
}

export default function ProcessingPage() {
  return (
    <Suspense
      fallback={
        <CsPage>
          <p className="text-sm text-ui-accent-readable">Loading processing plant…</p>
        </CsPage>
      }
    >
      <ProcessingPageInner />
    </Suspense>
  );
}
