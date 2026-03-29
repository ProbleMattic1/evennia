"use client";

import { Suspense, useCallback, useState } from "react";
import { useSearchParams } from "next/navigation";

import { CsButtonLink, CsColumns, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { CommodityTickerStrip, CommodityTickerTable } from "@/components/commodity-ticker";
import { ExitGrid } from "@/components/exit-grid";
import { StoryPanel } from "@/components/story-panel";
import { getProcessingState, playInteract } from "@/lib/ui-api";
import type { ProcessingState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

function StatRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-2 border-b border-zinc-100 py-1.5 last:border-0 dark:border-cyan-900/30">
      <span className="text-[12px] text-ui-muted">{label}</span>
      <span className="font-mono text-sm font-semibold tabular-nums text-zinc-800 dark:text-zinc-200">{value}</span>
    </div>
  );
}

function StorageBar({ used, capacity }: { used: number; capacity: number }) {
  const pct = capacity > 0 ? Math.min(100, (used / capacity) * 100) : 0;
  const color =
    pct < 60 ? "bg-emerald-500" : pct < 85 ? "bg-amber-400" : "bg-red-500";
  return (
    <div className="mt-1">
      <div className="flex justify-between text-[11px] text-ui-muted mb-0.5">
        <span>{used.toLocaleString(undefined, { maximumFractionDigits: 1 })} t used</span>
        <span>{capacity.toLocaleString(undefined, { maximumFractionDigits: 0 })} t cap</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-zinc-200 dark:bg-cyan-950/50">
        <div
          className={`h-1.5 rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function MinerSection({ data }: { data: ProcessingState }) {
  const { myOreQueued, myRefinedOutput, myRefinedOutputValue, myHaulers, processingFeeRate } =
    data;

  if (myOreQueued === null) {
    return (
      <section>
        <div className="mb-1 text-[10px] font-bold uppercase tracking-widest text-cyan-300">Your Activity</div>
        <p className="mt-1 text-[12px] text-ui-accent-readable">Sign in to see your ore queue and output.</p>
      </section>
    );
  }

  const hasOutput = myRefinedOutput && Object.keys(myRefinedOutput).length > 0;

  return (
    <section>
      <div className="mb-1 text-[10px] font-bold uppercase tracking-widest text-cyan-300">Your Activity</div>
      <div className="mt-1 space-y-0.5">
        <StatRow
          label="Ore queued for processing"
          value={`${myOreQueued.toLocaleString(undefined, { maximumFractionDigits: 1 })} t`}
        />
        {myRefinedOutputValue !== null && (
          <StatRow
            label={`Refined output (gross, before ${(processingFeeRate * 100).toFixed(0)}% fee)`}
            value={
              <>
                {myRefinedOutputValue.toLocaleString()}{" "}
                <span className="text-amber-700 dark:text-amber-400">cr</span>
              </>
            }
          />
        )}
        {myRefinedOutputValue !== null && myRefinedOutputValue > 0 && (
          <StatRow
            label="Net payout after fee"
            value={
              <>
                {Math.floor(myRefinedOutputValue * (1 - processingFeeRate)).toLocaleString()}{" "}
                <span className="text-amber-700 dark:text-amber-400">cr</span>
              </>
            }
          />
        )}
      </div>

      {hasOutput && (
        <p className="mt-2 text-[12px] text-ui-accent-readable">
          Collect your output with{" "}
          <code className="rounded bg-zinc-100 px-1 py-0.5 font-mono text-[11px] text-zinc-700 dark:bg-cyan-950/50 dark:text-cyan-300">
            collectrefined
          </code>{" "}
          at the Processing Plant.
        </p>
      )}

      {myHaulers && myHaulers.length > 0 && (
        <div className="mt-2">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-ui-accent-readable">
            Hauler delivery
          </p>
          <div className="mt-1 space-y-0.5">
            {myHaulers.map((h) => (
              <div key={h.id} className="flex items-center justify-between gap-2">
                <span className="truncate text-[12px] text-ui-muted dark:text-zinc-300">{h.key}</span>
                <span className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-[11px] font-medium text-ui-soft ring-1 ring-zinc-200 dark:bg-cyan-950/40 dark:text-cyan-300 dark:ring-cyan-800/50">
                  {h.deliveryMode === "ore_receiving_bay" ? "Ore Receiving Bay" : h.deliveryMode}
                </span>
              </div>
            ))}
          </div>
          <p className="mt-1.5 text-[11px] text-ui-accent-readable">
            At the plant, haulers unload into the Ore Receiving Bay and you are paid on delivery. Use
            feedrefinery to move ore from the bay into refining when you want processing; collectrefined
            for refined payout. For a personal processor, use feedprocessor in that room.
          </p>
        </div>
      )}
    </section>
  );
}

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
    <div className="mt-1 space-y-1">
      <p className="text-[11px] text-ui-accent-readable">
        Requires your character to be at the plant in-game. Accept or complete contracts via{" "}
        <code className="font-mono text-[10px]">play/interact</code> with{" "}
        <code className="font-mono text-[10px]">contractboard</code> and payload{" "}
        <code className="font-mono text-[10px]">action: accept | complete</code>,{" "}
        <code className="font-mono text-[10px]">contractId</code>.
      </p>
      <button
        type="button"
        disabled={busy}
        onClick={() => void runList()}
        className="rounded border border-cyan-700/50 bg-cyan-950/40 px-2 py-1 text-[12px] text-cyan-400 hover:bg-cyan-900/50 disabled:opacity-50"
      >
        {busy ? "…" : "List open contracts (game log)"}
      </button>
      {error ? <p className="text-[11px] text-red-500">{error}</p> : null}
      {notice ? <p className="text-[11px] text-ui-accent-readable">{notice}</p> : null}
    </div>
  );
}

function ProcessingPageInner() {
  const searchParams = useSearchParams();
  const venue = searchParams.get("venue")?.trim() || undefined;
  const loader = useCallback(() => getProcessingState(venue), [venue]);
  const { data, error, loading } = useUiResource(loader);

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

  return (
    <CsPage>
      <CsHeader
        title={data.plantName}
        subtitle={data.roomName}
        actions={<CsButtonLink href="/">Back to dashboard</CsButtonLink>}
      />
      <CsColumns
        left={
          <>
            <CsPanel title="Destinations">
              <ExitGrid exits={data.exits} />
            </CsPanel>
            <CsPanel title="Plant Output">
              <StoryPanel title="Plant Output" lines={data.storyLines} />
            </CsPanel>
            <CsPanel title="Ore Receiving Bay">
              <StorageBar used={data.rawStorageUsed} capacity={data.rawStorageCapacity} />
              <div className="mt-2 space-y-0.5">
                <StatRow
                  label="Plant buys your raw (from bay / storage)"
                  value={`${(data.rawSaleFeeRate * 100).toFixed(0)}% hassle fee on bid total; you receive the rest`}
                />
                <StatRow
                  label="You buy raw from the plant"
                  value={`Ask = bid + ${(data.rawAskPremiumRate * 100).toFixed(0)}%`}
                />
              </div>
            </CsPanel>
            <CsPanel title="Procurement board">
              <ProcurementBoardPanel />
            </CsPanel>
          </>
        }
        right={
          <>
            <CsPanel title="Market Snapshot">
              <CommodityTickerStrip />
            </CsPanel>
            <CsPanel title="Shared Refinery">
              <div className="mt-1 space-y-0.5">
                <StatRow
                  label="Shared pool input"
                  value={`${data.refineryInputTons.toLocaleString(undefined, { maximumFractionDigits: 1 })} t`}
                />
                <StatRow
                  label="Shared pool output value"
                  value={
                    <>
                      {data.refineryOutputValue.toLocaleString()}{" "}
                      <span className="text-amber-700 dark:text-amber-400">cr</span>
                    </>
                  }
                />
                <StatRow
                  label="Attributed ore queue (all miners)"
                  value={`${data.minerQueueOreTons.toLocaleString(undefined, { maximumFractionDigits: 1 })} t`}
                />
                <StatRow
                  label="Attributed output value (gross)"
                  value={
                    <>
                      {data.minerOutputValueTotal.toLocaleString()}{" "}
                      <span className="text-amber-700 dark:text-amber-400">cr</span>
                    </>
                  }
                />
                <StatRow label="Processing fee" value={`${(data.processingFeeRate * 100).toFixed(0)}%`} />
              </div>
            </CsPanel>
            <CsPanel title="Your Activity">
              <MinerSection data={data} />
            </CsPanel>
            <CsPanel title="Commodity Board">
              <CommodityTickerTable />
            </CsPanel>
          </>
        }
      />
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
