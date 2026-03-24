"use client";

import { useCallback } from "react";
import Link from "next/link";

import { ExitGrid } from "@/components/exit-grid";
import { StoryPanel } from "@/components/story-panel";
import { getProcessingState } from "@/lib/ui-api";
import type { ProcessingState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2 border-b border-zinc-100 py-1.5 last:border-0">
      <span className="text-[12px] text-zinc-500">{label}</span>
      <span className="font-mono text-sm font-semibold tabular-nums text-zinc-800">{value}</span>
    </div>
  );
}

function StorageBar({ used, capacity }: { used: number; capacity: number }) {
  const pct = capacity > 0 ? Math.min(100, (used / capacity) * 100) : 0;
  const color =
    pct < 60 ? "bg-emerald-500" : pct < 85 ? "bg-amber-400" : "bg-red-500";
  return (
    <div className="mt-1">
      <div className="flex justify-between text-[11px] text-zinc-500 mb-0.5">
        <span>{used.toLocaleString(undefined, { maximumFractionDigits: 1 })} t used</span>
        <span>{capacity.toLocaleString(undefined, { maximumFractionDigits: 0 })} t cap</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-zinc-200">
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
      <section className="border-b border-zinc-100 px-2 py-2">
        <h2 className="section-label">Your Activity</h2>
        <p className="mt-1 text-[12px] text-zinc-400">Sign in to see your ore queue and output.</p>
      </section>
    );
  }

  const hasOutput = myRefinedOutput && Object.keys(myRefinedOutput).length > 0;

  return (
    <section className="border-b border-zinc-100 px-2 py-2">
      <h2 className="section-label">Your Activity</h2>
      <div className="mt-1 space-y-0.5">
        <StatRow
          label="Ore queued for processing"
          value={`${myOreQueued.toLocaleString(undefined, { maximumFractionDigits: 1 })} t`}
        />
        {myRefinedOutputValue !== null && (
          <StatRow
            label={`Refined output (gross, before ${(processingFeeRate * 100).toFixed(0)}% fee)`}
            value={`${myRefinedOutputValue.toLocaleString()} cr`}
          />
        )}
        {myRefinedOutputValue !== null && myRefinedOutputValue > 0 && (
          <StatRow
            label="Net payout after fee"
            value={`${Math.floor(myRefinedOutputValue * (1 - processingFeeRate)).toLocaleString()} cr`}
          />
        )}
      </div>

      {hasOutput && (
        <p className="mt-2 text-[12px] text-zinc-500">
          Collect your output with{" "}
          <code className="rounded bg-zinc-100 px-1 py-0.5 font-mono text-[11px] text-zinc-700">
            collectrefined
          </code>{" "}
          at the Processing Plant.
        </p>
      )}

      {myHaulers && myHaulers.length > 0 && (
        <div className="mt-2">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
            Hauler Delivery Modes
          </p>
          <div className="mt-1 space-y-0.5">
            {myHaulers.map((h) => (
              <div key={h.key} className="flex items-center justify-between gap-2">
                <span className="truncate text-[12px] text-zinc-600">{h.key}</span>
                <span
                  className={`rounded px-1.5 py-0.5 font-mono text-[11px] font-medium ${
                    h.deliveryMode === "process"
                      ? "bg-amber-50 text-amber-700 ring-1 ring-amber-200"
                      : "bg-zinc-100 text-zinc-600"
                  }`}
                >
                  {h.deliveryMode}
                </span>
              </div>
            ))}
          </div>
          <p className="mt-1.5 text-[11px] text-zinc-400">
            Change with{" "}
            <code className="font-mono text-[11px]">setdelivery &lt;hauler&gt; sell|process</code>
          </p>
        </div>
      )}
    </section>
  );
}

export default function ProcessingPage() {
  const loader = useCallback(() => getProcessingState(), []);
  const { data, error, loading } = useUiResource(loader);

  if (loading) {
    return (
      <main className="main-content">
        <p className="text-sm text-zinc-500">Loading processing plant…</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="main-content">
        <p className="text-sm text-red-600">
          Failed to load processing plant: {error ?? "Unknown error"}
        </p>
      </main>
    );
  }

  return (
    <main className="main-content">
      <header className="flex items-center justify-between border-b border-zinc-200 py-3 dark:border-zinc-700">
        <div className="px-2">
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">{data.plantName}</h1>
          <p className="mt-0.5 text-[12px] text-zinc-500">{data.roomName}</p>
        </div>
        <Link
          href={`/play?room=${encodeURIComponent(data.roomName)}`}
          className="rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-800 hover:bg-zinc-100"
        >
          Back to Play
        </Link>
      </header>

      <div className="grid gap-2 px-2 py-2 lg:grid-cols-[1.5fr_1fr]">
        <StoryPanel title="Plant Output" lines={data.storyLines} />

        <div className="flex flex-col gap-2">
          <section className="border-b border-zinc-100 px-2 py-2">
            <h2 className="section-label">Ore Receiving Bay</h2>
            <StorageBar used={data.rawStorageUsed} capacity={data.rawStorageCapacity} />
          </section>

          <section className="border-b border-zinc-100 px-2 py-2">
            <h2 className="section-label">Shared Refinery</h2>
            <div className="mt-1 space-y-0.5">
              <StatRow
                label="Input queue"
                value={`${data.refineryInputTons.toLocaleString(undefined, { maximumFractionDigits: 1 })} t`}
              />
              <StatRow
                label="Output value"
                value={`${data.refineryOutputValue.toLocaleString()} cr`}
              />
              <StatRow
                label="Processing fee"
                value={`${(data.processingFeeRate * 100).toFixed(0)}%`}
              />
            </div>
          </section>

          <MinerSection data={data} />

          <ExitGrid exits={data.exits} />
        </div>
      </div>
    </main>
  );
}
